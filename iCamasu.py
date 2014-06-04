#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = "Raul Siles"
__email__     = "raul@dinosec.com"
__copyright__ = "Copyright (c) 2014 DinoSec SL (www.dinosec.com)"
__license__   = "GPL"
__version__   = "0.41"
__date__      = "2014-05-29"

import plistlib
import argparse
import os
import sys
import hashlib
import binascii
from collections import defaultdict

# -- iCamasu --

# Latest iOS version whose PLIST file has been tested:
ios_version_tested = "7.1.1"

asciiart = '''
           ,gggg,
  OO     ,88"""Y8b,
        d8"     `Y8
  gg   d8'   8b  d8
  gg  ,8I    "Y88P'
  gg  I8'         ,gggg,gg   ,ggg,,ggg,,ggg,     ,gggg,gg    ,g,     gg      gg
  88  d8         dP"  "Y8I  ,8" "8P" "8P" "8,   dP"  "Y8I   ,8'8,    I8      8I
  88  Y8,       i8'    ,8I  I8   8I   8I   8I  i8'    ,8I  ,8'  Yb   I8,    ,8I
_,88,_`Yba,,__,,d8,   ,d8b,,dP   8I   8I   Yb,,d8,   ,d8b,,8'_   8) ,d8b,  ,d8b
8P""Y8  `"Y888 P"Y8888P"`Y88P'   8I   8I   `Y8P"Y8888P"`Y8P' "YY8P8P8P'"Y88P"`Y8
'''

# ----
# Variables:

verbose = False
full_details = False

# File variables
input_file = "com_apple_MobileAsset_SoftwareUpdate.xml"
filesize = 0
filesha1 = ""

# URL variables
url    = "http://mesu.apple.com/assets/com_apple_MobileAsset_SoftwareUpdate/com_apple_MobileAsset_SoftwareUpdate.xml"
urldoc = "http://mesu.apple.com/assets/com_apple_MobileAsset_SoftwareUpdateDocumentation/" \
         "com_apple_MobileAsset_SoftwareUpdateDocumentation.xml"

# PLIST file entries or assets (dictionaries)
assets = defaultdict(list)
assets_by_ios_version = defaultdict(list)

# Total number of assets or entries
num_assets = 0
# Total number of devices
num_devices = 0
# Total number of iOS versions
num_versions = 0

# Minimum & maximum iOS versions
min_iOS_version = ""
max_iOS_version = ""

# Are there any iOS beta versions?
has_beta_versions = False
beta_versions = []

# Selectors
device = ""
ios_version = ""
min_version = False
max_version = False
both_versions = False
summary = False
file_summary = False
summary_by_device = False
summary_by_ios_version = False

# Default response if an element/key is not found in a dictionary
default_response = "None"

# ----


# Print error message and exit
def error(msg):
    print("\n[!] ERROR - {0}\n".format(msg))
    sys.exit(1)


# Print warning message and continue
def warning(msg):
    print("[/] WARNING - {0}".format(msg))


# Return file size
def fileSize(filename):
    try:
        return os.path.getsize(filename)
    except os.error as e:
        error("File does not exist: {0} ({1})".format(filename, e))


# Return file SHA-1 hash
def fileSHA1(filename):
    with open(filename, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


# Check if version is less than the minimum iOS version already found
def isMiniOSVersion(version, current_min_ios_version):
    if current_min_ios_version == "":
        return True
    elif version < current_min_ios_version:
        return True
    else:
        return False


# Check if version is greater than the maximum iOS version already found
def isMaxiOSVersion(version, current_max_ios_version):
    if current_max_ios_version == "":
        return True
    elif version > current_max_ios_version:
        return True
    else:
        return False


# Parse PLIST file
def parse(infile):

    global min_iOS_version
    global max_iOS_version
    global has_beta_versions

    count = 0

    plist = plistlib.readPlist(infile)
    #list_of_assets = plist["Assets"]
    list_of_assets = plist.get("Assets", default_response)
    #print list_of_assets
    if list_of_assets == default_response:
        error("The 'Assets' key is not available in the PLIST file: {0}".format(infile))

    for entry in list_of_assets:

        # Apple device(s) - list
        devices = entry.get("SupportedDevices", default_response)
        if devices == default_response:
            warning("There is no 'SupportedDevices' key for entry {0}.".format(count+1))

        product = entry.get("SUProductSystemName", default_response)
        if product == default_response:
            warning("There is no 'SUProductSystemName' key for entry {0}.".format(count+1))
        elif product != "iOS":
            error("Product name different from 'iOS': {0}".format(product))

        publisher = entry.get("SUPublisher", default_response)
        if publisher == default_response:
            warning("There is no 'SUPublisher' key for entry {0}.".format(count+1))
        elif publisher != "Apple Inc.":
            error("Publisher different from Apple: {0}".format(publisher))

        # Documentation ID (string)
        documentationID = entry.get("SUDocumentationID", default_response)

        # iOS version (string) & Prerequisite iOS version (string)
        version = entry.get("OSVersion", default_response)
        # Add iOS beta version details, if available:
        release_type = entry.get("ReleaseType", default_response)
        if version == default_response:
            warning("There is no 'OSVersion' key for entry {0}.".format(count+1))
        else:
            if release_type != default_response:
                if release_type != "Beta":
                    warning("Release type key different from 'Beta': {0}".format(release_type))
                else:
                    has_beta_versions = True
                    if documentationID != default_response:
                        version = version + "(" + documentationID + ")"
                        if version not in beta_versions:
                            beta_versions.append(version)

        # Min & max iOS versions
        if isMiniOSVersion(version, min_iOS_version):
            min_iOS_version = version
        if isMaxiOSVersion(version, max_iOS_version):
            max_iOS_version = version

        # "PrerequisiteOSVersion" might not exist = None
        fromVersion = entry.get("PrerequisiteOSVersion", default_response)

        # Build (string) & Prerequisite Build (string)
        # ("PrerequisiteBuild" (and other entries) might not exist = "None")
        build = entry.get("Build", default_response)
        preBuild = entry.get("PrerequisiteBuild", default_response)

        # Installation size (string)
        installSize = entry.get("InstallationSize", default_response)

        # Download size (integer)
        downloadSize = entry.get("_DownloadSize", default_response)

        # Unarchived size (integer)
        unarchivedSize = entry.get("_UnarchivedSize", default_response)

        # Download format (string)
        fileFormat = entry.get("_CompressionAlgorithm", default_response)
        if fileFormat != "zip":
            warning("Download file format different from ZIP: {0}".format(fileFormat))

        # Base URL (string)
        baseURL = entry.get("__BaseURL", default_response)
        # Path (string)
        path = entry.get("__RelativePath", default_response)
        if baseURL == default_response or path == default_response:
            warning("There is no '__BaseURL' or '__RelativePath' key for entry {0}.".format(count+1))
        url_entry = baseURL+path

        # Hash format (string)
        hashFormat = entry.get("_MeasurementAlgorithm", default_response)
        # Encoded hash (data - in Base64)
        value = entry.get("_Measurement")
        hash_value = str("None" if value is None else binascii.b2a_hex(value.data))

        # In iOS 7 PLIST files there can be more than one Apple device for a single iOS entry
        #
        #if len(devices) > 1:
        #    error("There is more than one Apple device for an entry: {0}".format(devices))
        #else:
        #    dev = devices[0]
        #

        for dev in devices:

            # Asset id (from 1 to N)
            count += 1

            # Add details from this entry to assets
            new_entry = {version: {}}
            #new_entry[version]['version']       = version
            new_entry[version]['fromVersion']    = fromVersion
            new_entry[version]['build']          = build
            new_entry[version]['preBuild']       = preBuild
            new_entry[version]['installSize']    = installSize
            new_entry[version]['downloadSize']   = downloadSize
            new_entry[version]['unarchivedSize'] = unarchivedSize
            new_entry[version]['fileFormat']     = fileFormat
            #new_entry[version]['baseURL']       = baseURL
            #new_entry[version]['path']          = path
            new_entry[version]['url']            = url_entry
            new_entry[version]['hashFormat']     = hashFormat
            new_entry[version]['hash']           = hash_value
            new_entry[version]['beta']           = True if release_type != default_response else False

            # Add a new entry to the list of assets for this device
            assets[dev].append(new_entry)

    # Return total number of assets or entries
    return count


# Get assets classified by iOS version
def getAssetsByiOSVersion():
    global assets_by_ios_version
    for dev in assets:
        for entry in assets[dev]:
            for ver in entry.keys():
                assets_by_ios_version[ver].append(dev)


# Get (sorted & unique) list of iOS versions for a specific device
def iOSVersionsFor(this_device):
    if assets.get(this_device, default_response) == default_response:
        return default_response
    else:
        versions = []
        for entry in assets[this_device]:
            for ver in entry.keys():
                versions.append(ver)
        return sorted(set(versions))


# Get (sorted & unique) list of devices for a specific iOS version
def devicesFor(this_ios_version):
    return assets_by_ios_version.get(this_ios_version, default_response)


#  PRINT & SUMMARY FUNCTIONS:
# ----------------------------

# Print minimum version
def miniOSVersion():
    print min_iOS_version


# Print maximum version
def maxiOSVersion():
    print max_iOS_version


# Print one-line summary of an asset
def onelineSummaryOfAsset(count, dev, version, entry):
    beta = " (beta)" if entry[version]["beta"] else ""
    print "[%d] %s: %s (%s) [from version %s (%s)]%s %s" % (count, dev, version,
            entry[version]['build'], entry[version]['fromVersion'], entry[version]['preBuild'],
            beta, entry[version]["hash"])


# Print full summary of an asset
def assetSummary(count, dev, version, entry):
    beta = " (beta)" if entry[version]["beta"] else ""
    print "[%d]" % count
    print "%s: %s (%s) [from version %s (%s)]%s" \
          % (dev, version, entry[version]['build'],
             entry[version]['fromVersion'], entry[version]['preBuild'], beta)
    print "Size: %s (%s) --> %s (Install: %s)" \
          % (entry[version]['downloadSize'], entry[version]['fileFormat'],
             entry[version]['unarchivedSize'], entry[version]['installSize'])
    print "URL: %s" % (entry[version]["url"])
    print "%s: %s" % (entry[version]["hashFormat"], entry[version]["hash"])


# Print details for assets for a specific device
def printAssetsForDevice(this_device):
    print "- Assets Details for Device %s: " % this_device
    print ""
    count = 0
    # Print sorted list of assets and all their associated details for a specific device
    for entry in sorted(assets[this_device]):
        for version in entry.keys():
            count += 1
            if not full_details:
                onelineSummaryOfAsset(count, device, version, entry)
            else:
                assetSummary(count, device, version, entry)
                print


# Print details for assets for a specific iOS version
def printAssetsForiOSVersion(this_ios_version):
    print "- Assets Details for iOS Version %s: " % this_ios_version
    print ""
    count = 0
    # Print sorted list of assets and all their associated details for a specific iOS version
    for dev in sorted(assets):
        for entry in sorted(assets[dev]):
            for version in entry.keys():
                if version == this_ios_version:
                    count += 1
                    if not full_details:
                        onelineSummaryOfAsset(count, dev, version, entry)
                    else:
                        assetSummary(count, dev, version, entry)
                        print


# Print details for all assets in PLIST file
def printAssets():
    #print assets
    print "- PLIST File Details: (%d assets)" % num_assets
    print ""
    count = 0
    # Print sorted list of assets and all their associated details
    for dev in sorted(assets):
        for entry in sorted(assets[dev]):
            for version in entry.keys():
                count += 1
                if not full_details:
                    onelineSummaryOfAsset(count, dev, version, entry)
                else:
                    assetSummary(count, dev, version, entry)
                    print


# Print one-line summary of PLIST file
def summaryOneLine():
    beta = " (beta)" if has_beta_versions else ""
    print "%s (SHA-1: %s) = %s bytes, %s assets, %s devices, %s versions%s, min: %s, max: %s" % \
          (input_file, filesha1, filesize, num_assets, num_devices, num_versions, beta, min_iOS_version, max_iOS_version)


# Print summary of PLIST file
def summaryFile():
    beta = " (beta)" if has_beta_versions else ""

    print "- File Summary: "
    print ""
    print "Filename:        %s" % input_file
    print "SHA1:            %s" % filesha1
    print "Size:            %d" % filesize
    print "# Assets:        %d" % num_assets
    print "# Devices:       %d" % num_devices
    print "# iOS versions:  %d%s" % (num_versions, beta)
    print "Min. iOS:        %s" % min_iOS_version
    print "Max. iOS:        %s" % max_iOS_version
    if has_beta_versions:
        print "# Beta versions: %d" % len(beta_versions)
        print "Beta versions:   %s" % " ".join(sorted(set(beta_versions)))


# Print summary of PLIST file by model
def summaryByDevice():
    print "- Summary By Device: (%d devices)" % num_devices
    print ""
    # Print (sorted & unique) list of devices and (sorted & unique) associated iOS versions
    for dev in sorted(assets):
        print "%s: %s" % (dev, " ".join(iOSVersionsFor(dev)))


# Print summary of PLIST file by iOS version
def summaryByiOSVersion():
    print "- Summary By iOS Version: (%d iOS versions)" % num_versions
    print ""
    # Print (sorted & unique) list of iOS versions and associated devices
    for ver, assets_list in sorted(assets_by_ios_version.items()):
        print "%s: %s" % (ver, " ".join(sorted(set(assets_list))))


# Print (sorted & unique) list of iOS versions for a specific device
def summaryiOSVersionsFor(this_device):
    versions = iOSVersionsFor(this_device)
    if versions == default_response:
        print "%s" % default_response
    else:
        print "%s" % (" ".join(sorted(set(versions))))


# Print (sorted & unique) list of devices for a specific iOS version
def summaryDevicesFor(this_ios_version):
    devices = devicesFor(this_ios_version)
    if devices == default_response:
        print "%s" % default_response
    else:
        print "%s" % (" ".join(sorted(set(devices))))



#  MAIN:
# -------

if __name__ == "__main__":

    header_info = "\n\tiCamasu: iOS com_apple_MobileAsset_SoftwareUpdate\n\t         (v" + __version__ + \
             " - " + __date__ + ")\n\n\t" + __copyright__ + " - " + __author__ + "\n"
    header_description = "\tTool that parses and extracts details from Apple iOS software\n" + \
             "\tupdate PLIST files: com_apple_MobileAsset_SoftwareUpdate.xml.\n"
    header = asciiart + header_info
    header_tested = "\t(v" + __version__ + " - PLIST file tested up to iOS version " + ios_version_tested + ")\n\n"

    # Parse arguments...
    parser = argparse.ArgumentParser(description=asciiart + "\n" + header_info + "\n" +
             header_description + header_tested,
             formatter_class=argparse.RawTextHelpFormatter,
             epilog='\t-- Check the new details about the latest iOS updates! --')

    # General flags:
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Increase output verbosity (default = off)")
    parser.add_argument("-f", "--file", help="iOS software update PLIST file:\n" +
                        "(e.g. com_apple_MobileAsset_SoftwareUpdate.xml)")
    parser.add_argument("-V", "--version", action='version', version=__version__,
                        help="Show version information and exit.")
    parser.add_argument("-F", "--full-details", action="store_true",
                                 help="Show full details for assets.")

    # Output selectors
    group_selectors = parser.add_mutually_exclusive_group()
    group_selectors.add_argument("-s", "--summary", action="store_true",
                                 help="Show one-line PLIST file summary (default = on).")
    group_selectors.add_argument("-S", "--file-summary", action="store_true",
                                 help="Show PLIST file summary.\n(optional: use with '-v' or '-vF')")
    group_selectors.add_argument("-d", "--device",
                                 help="Show iOS version for this device.\n(optional: use with '-v' or '-vF')")
    group_selectors.add_argument("-i", "--ios-version",
                                 help="Show devices for this iOS version.\n(optional: use with '-v' or '-vF')")
    group_selectors.add_argument("-D", "--summary-by-device", action="store_true",
                                 help="Show PLIST file summary by device.")
    group_selectors.add_argument("-I", "--summary-by-ios-version", action="store_true",
                                 help="Show PLIST file summary by iOS version.")
    group_selectors.add_argument("-m", "--min-version", action="store_true",
                                 help="Show minimum iOS version.")
    group_selectors.add_argument("-M", "--max-version", action="store_true",
                                 help="Show maximum iOS version.")
    group_selectors.add_argument("-b", "--both-versions", action="store_true",
                                 help="Show both minimum & maximum iOS version.")

    args = parser.parse_args()

    if args.file is not None:
        input_file = args.file
    else:
        input_file = "com_apple_MobileAsset_SoftwareUpdate.xml"
        #parser.print_help()
        #error("It is mandatory to specify the input file name.")

    if args.verbose:
        verbose = args.verbose

    if args.full_details:
        full_details = args.full_details

    if args.device is not None:
        device = args.device
    elif args.ios_version is not None:
        ios_version = args.ios_version
    elif args.min_version:
        min_version = args.min_version
    elif args.max_version:
        max_version = args.max_version
    elif args.both_versions:
        both_versions = args.both_versions
    elif args.summary:
        summary = args.summary
    elif args.file_summary:
        file_summary = args.file_summary
    elif args.summary_by_device:
        summary_by_device = args.summary_by_device
    elif args.summary_by_ios_version:
        summary_by_ios_version = args.summary_by_ios_version
    else:
        # Show a one-line summary of the PLIST file (default output)
        summary = True


    # Process PLIST file
    filesize = fileSize(input_file)
    filesha1 = fileSHA1(input_file)

    # Parse PLIST file (and get total number of assets or entries)
    num_assets = parse(input_file)

    # Classify assets by iOS version
    getAssetsByiOSVersion()

    # Total number of devices and iOS versions
    num_devices = len(assets)
    num_versions = len(assets_by_ios_version)

    # Sort iOS beta versions list
    beta_versions.sort()

    if device: # If is not an empty string
        if not verbose:
            summaryiOSVersionsFor(device)
        else:
            print
            print(header)
            printAssetsForDevice(device)
            #print
    elif ios_version: # If is not an empty string
        if not verbose:
            summaryDevicesFor(ios_version)
        else:
            print
            print(header)
            printAssetsForiOSVersion(ios_version)
            #print
    elif min_version:
        miniOSVersion()
    elif max_version:
        maxiOSVersion()
    elif both_versions:
        miniOSVersion()
        maxiOSVersion()
    elif summary:
        # Print one-line PLIST summary
        summaryOneLine()
    elif file_summary:
        if not verbose:
            # Print PLIST file summary
            print
            print(header)
            summaryFile()
            #print
        else:
            # Print full details from PLIST file
            print
            print(header)
            summaryFile()
            print
            printAssets()
            #print
    elif summary_by_device:
        # Print PLIST summary by device
        print
        print(header)
        summaryByDevice()
        #print
    elif summary_by_ios_version:
        # Print PLIST summary by iOS version
        print
        print(header)
        summaryByiOSVersion()
        #print
    else:
        # Default:
        # Print one-line PLIST summary
        summaryOneLine()
