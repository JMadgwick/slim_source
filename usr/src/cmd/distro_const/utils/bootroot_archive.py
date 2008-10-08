#!/usr/bin/python
#
# CDDL HEADER START
#
# The contents of this file are subject to the terms of the
# Common Development and Distribution License (the "License").
# You may not use this file except in compliance with the License.
#
# You can obtain a copy of the license at usr/src/OPENSOLARIS.LICENSE
# or http://www.opensolaris.org/os/licensing.
# See the License for the specific language governing permissions
# and limitations under the License.
#
# When distributing Covered Code, include this CDDL HEADER in each
# file and include the License file at usr/src/OPENSOLARIS.LICENSE.
# If applicable, add the following below this CDDL HEADER, with the
# fields enclosed by brackets "[]" replaced with your own identifying
# information: Portions Copyright [yyyy] [name of copyright owner]
#
# CDDL HEADER END
#
# Copyright 2008 Sun Microsystems, Inc.  All rights reserved.
# Use is subject to license terms.
#

# =============================================================================
# =============================================================================
# bootroot_archive - Release the bootroot mount and archive the bootroot area.
# =============================================================================
# =============================================================================

import os
import sys
import signal
from subprocess import Popen, PIPE
from osol_install.ManifestRead import ManifestRead
from osol_install.distro_const.DC_ti import ti_create_target
from osol_install.distro_const.DC_ti import ti_release_target
from osol_install.distro_const.dc_utils import get_manifest_value
from osol_install.distro_const.DC_defs import BOOT_ROOT_COMPRESSION_LEVEL
from osol_install.distro_const.DC_defs import BOOT_ROOT_COMPRESSION_TYPE
from osol_install.distro_const.DC_defs import BOOT_ROOT_SIZE_PAD
from osol_install.distro_const.DC_defs import BR_FILENAME

execfile('/usr/lib/python2.4/vendor-packages/osol_install/ti_defs.py')

# A few commands
AWK = "/usr/bin/awk"
CD = "cd"		# Built into the shell
CMD7ZA = "/usr/bin/7za"
CPIO = "/usr/bin/cpio"
DU = "/usr/bin/du"
FIND = "/usr/bin/find"
MV = "/usr/bin/mv"
TUNEFS = "/usr/sbin/tunefs"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def create_target_intr_handler(signum, frame):
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	""" Cleanup when ^C received in the middle of a ti_create_target() call.

	Args:
	  signum: signal number (not used)

	  frame: stack frame number (not used)

	Returns: N/A

	Raises: N/A
	"""
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	print "^C detected.  Cleaning up..."
	ti_release_target({
	    TI_ATTR_TARGET_TYPE:TI_TARGET_TYPE_DC_RAMDISK,
	    TI_ATTR_DC_RAMDISK_DEST: BR_LOFI_MNT_PT,
	    TI_ATTR_DC_RAMDISK_FS_TYPE: TI_DC_RAMDISK_FS_TYPE_UFS,
	    TI_ATTR_DC_RAMDISK_BOOTARCH_NAME: BR_ARCHFILE })
	sys.exit(0)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Main
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
""" Release the bootroot mount and archive the bootroot area.

Args:
  MFEST_SOCKET: Socket needed to get manifest data via ManifestRead object

  PKG_IMG_MNT_PT: Package image area mountpoint

  TMP_DIR: Temporary directory to contain the bootroot file

  BR_BUILD: Area where bootroot is put together.

  MEDIA_DIR: Area where the media is put. (Not used)
"""
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if (len(sys.argv) != 6): # Don't forget sys.argv[0] is the script itself.
	raise Exception, (sys.argv[0] + ": Requires 5 args:\n" +
	    "    Reader socket, pkg_image area, tmp dir,\n"
	    "    bootroot build area, media area.")

# Collect input arguments from what this script sees as a commandline.
MFEST_SOCKET = sys.argv[1]	# Manifest reader socket
PKG_IMG_MNT_PT = sys.argv[2]	# package image area mountpoint
TMP_DIR = sys.argv[3]		# temporary directory to contain bootroot file
BR_BUILD = sys.argv[4]		# Bootroot build area

# Destination and name of bootroot file.
BR_ARCHFILE = PKG_IMG_MNT_PT + BR_FILENAME

# Location of the lofi file mountpoint, known only to this file.
BR_LOFI_MNT_PT = TMP_DIR + "/br_lofimnt"

# get the manifest reader object from the socket
manifest_reader_obj = ManifestRead(MFEST_SOCKET)

# Bootroot compression type and level, and padding amount.
BR_COMPR_LEVEL = get_manifest_value(manifest_reader_obj,
    BOOT_ROOT_COMPRESSION_LEVEL)
if (BR_COMPR_LEVEL == None):
	raise Exception, (sys.argv[0] +
	    ": bootroot compression level missing from manifest")

BR_COMPR_TYPE = get_manifest_value(manifest_reader_obj,
    BOOT_ROOT_COMPRESSION_TYPE)
if (BR_COMPR_TYPE == None):
	raise Exception, (sys.argv[0] +
	    ": bootroot compression type missing from manifest")

padding = -1
br_pad_size_str = get_manifest_value(manifest_reader_obj,
    BOOT_ROOT_SIZE_PAD)
if (br_pad_size_str != None):
	try:
		padding = int(br_pad_size_str)
	except:
		pass
if (padding < 0):
	raise Exception, (sys.argv[0] +
	    ": Bootroot padding size is missing from manifest or invalid.")

# Remove any old stale archive.
gz_arch_file = BR_ARCHFILE + ".gz"
if (os.path.exists(gz_arch_file)):
	os.remove(gz_arch_file)
if (os.path.exists(BR_ARCHFILE)):
	os.remove(BR_ARCHFILE)

print "Sizing bootroot requirements..."
cmd = DU + " -sk " + BR_BUILD + " | " + AWK + " '{print $1}'"
bootroot_size = int(Popen(cmd, shell=True,
    stdout=PIPE).communicate()[0].strip())

print "    Raw uncompressed: %d MB." % (bootroot_size / 1024)
bootroot_size += (padding * 1024)	# Convert padding to kbytes
print "Creating bootroot archive with padded size of %d MB..." % (
    (bootroot_size / 1024))

# Create the file for the bootroot and mount it
signal.signal (signal.SIGINT, create_target_intr_handler)
status = ti_create_target({
    TI_ATTR_TARGET_TYPE:TI_TARGET_TYPE_DC_RAMDISK,
    TI_ATTR_DC_RAMDISK_DEST: BR_LOFI_MNT_PT,
    TI_ATTR_DC_RAMDISK_FS_TYPE: TI_DC_RAMDISK_FS_TYPE_UFS,
    TI_ATTR_DC_RAMDISK_SIZE: bootroot_size,
    TI_ATTR_DC_RAMDISK_BOOTARCH_NAME: BR_ARCHFILE })
signal.signal (signal.SIGINT, signal.SIG_DFL)
if (status != 0):
	ti_release_target({
	    TI_ATTR_TARGET_TYPE:TI_TARGET_TYPE_DC_RAMDISK,
	    TI_ATTR_DC_RAMDISK_DEST: BR_LOFI_MNT_PT,
	    TI_ATTR_DC_RAMDISK_FS_TYPE: TI_DC_RAMDISK_FS_TYPE_UFS,
	    TI_ATTR_DC_RAMDISK_BOOTARCH_NAME: BR_ARCHFILE })
	raise Exception, (sys.argv[0] +
	    ": Unable to create boot archive: ti_create_target returned %d" %
	    status)

# Allow all space to be used.
# Saving 10% space as typical on UFS buys nothing for a ramdisk.
cmd = TUNEFS + " -m 0 " + BR_LOFI_MNT_PT + " >/dev/null"
copy_status = os.system(cmd)
if (copy_status != 0):	# Print a warning and forge ahead anyway...
	print >>sys.stderr, (
	    "Warning: Could not tunefs the bootroot to use all space")

# Copy files to the archive.
cmd = CD + " " + BR_BUILD + "; "
cmd += FIND + " . | " + CPIO + " -pdum " + BR_LOFI_MNT_PT
copy_status = os.system(cmd)

# Unmount the bootroot file and delete the lofi device
status = ti_release_target({
    TI_ATTR_TARGET_TYPE:TI_TARGET_TYPE_DC_RAMDISK,
    TI_ATTR_DC_RAMDISK_DEST: BR_LOFI_MNT_PT,
    TI_ATTR_DC_RAMDISK_FS_TYPE: TI_DC_RAMDISK_FS_TYPE_UFS,
    TI_ATTR_DC_RAMDISK_BOOTARCH_NAME: BR_ARCHFILE })
if (copy_status != 0):
	raise Exception, (sys.argv[0] + ": Error copying files to bootroot " +
	    "container;  find/cpio command returns %d" % status)

elif (status != 0):
	raise Exception, (sys.argv[0] +
	    ": Unable to release boot archive: ti_release_target returned %d" %
	    status)

if (BR_COMPR_TYPE == "none"):
	print "Skipping compression..."
else:
	print "Doing compression..."

	# archive file using 7zip command and gzip compression
	cmd = CMD7ZA + " a "
	if (BR_COMPR_TYPE == "gzip"):
		cmd += "-tgzip -mx=" + BR_COMPR_LEVEL + " "
	else:
		raise Exception, (sys.argv[0] + ": Unrecognized bootroot " +
		    "compression type: " + BR_COMPR_TYPE)
	cmd += BR_ARCHFILE + ".gz " + BR_ARCHFILE
	status = os.system(cmd)
	if (status != 0):
		raise Exception, (sys.argv[0] +
		    ": Error compressing bootroot: " +
		    "7za command returns %d" % status)

	# move compressed file to proper location in pkg image area
	mvcmd = MV + " " + BR_ARCHFILE + ".gz " + BR_ARCHFILE
	status = os.system(mvcmd)
	if (status != 0):
		raise Exception, (sys.argv[0] + ": Error moving " +
		    "bootroot from %s to %s: mv returns %d" %
		    (BR_ARCHFILE + '.gz', BR_ARCHFILE, status))

os.chmod(BR_ARCHFILE, 0644)

sys.exit(0)