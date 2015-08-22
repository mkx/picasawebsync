#!/usr/bin/python

import argparse
import fnmatch

from picasawebsync.albums import Albums
from picasawebsync.config import Config
from picasawebsync.consts import *








# start of the program

parser = argparse.ArgumentParser()

parser.add_argument(
    "-d",
    "--directory",
    nargs='+',
    help="The local directories. The first of these will be used for any "
    "downloaded items"
)

parser.add_argument(
    "-n",
    "--naming",
    default=defaultNamingFormat, nargs='+',
    help="Expression to convert directory names to web album names. Formed as "
    "a ~ seperated list of substitution strings, "
    "so if a sub directory is in the root scanning directory then the first "
    "element will be used, if there is a directory between them the second, "
    "etc. If the directory path is longer than the "
    "list then the last element is used (and thus the path is flattened). "
    "Default is \"%s\"" % defaultNamingFormat
)

parser.add_argument(
    "--namingextract",
    default=False,
    help="Naming extraction rules. It applies to the name computed according "
    "to naming options."
    "Search capturing pattern is seperated by a | from formatting expression "
    "(ex: '([0-9]{4})[0-9]*-(.*)|\2 (\2)'"
)

parser.add_argument(
    "-c",
    "--compareattributes",
    type=int,
    help="set of flags to indicate whether to use date (1), filesize (2), "
    "hash (4) in addition to filename. "
    "These are applied in order from left to right with a difference "
    "returning immediately and a similarity passing on to the next check."
    "They work like chmod values, so add the values in brackets to switch on "
    "a check. Date uses a 60 second margin (to allow for different time stamp"
    "between google and your local machine, and can only identify a locally "
    "modified file not a remotely modified one. Filesize and hash are used by "
    "default",
    default=3
)

parser.add_argument(
    "-v",
    "--verbose",
    default=False,
    action='store_true',
    help="Increase verbosity"
)

parser.add_argument(
    "-t",
    "--test",
    default=False,
    action='store_true',
    help="Don't actually run activities, but report what you would have done "
    "(you may want to enable verbose)"
)

parser.add_argument(
    "-m",
    "--mode",
    type=convertMode,
    help="The mode is a preset set of actions to execute in different "
    "circumstances, e.g. upload, download, sync, etc. The full set of "
    "options is %s. "
    "The default is upload. Look at the github page for full details of what "
    "each action does" % list(modes),
    default="upload"
)

parser.add_argument(
    "-dd",
    "--deletedups",
    default=False,
    action='store_true',
    help="Delete any remote side duplicates"
)

parser.add_argument(
    "-f",
    "--format",
    type=convertFormat,
    default="photo",
    help="Upload photos, videos or both"
)

parser.add_argument(
    "-s",
    "--skip",
    nargs='*',
    default=[],
    help="Skip (local) files or folders using a list of glob expressions."
)

parser.add_argument(
    "--skipserver",
    nargs='*',
    default=[],
    help="Skip (remote) files or folders using a list of glob expressions."
)

parser.add_argument(
    "--purge",
    default=False,
    action='store_true',
    help="Purge empty web filders"
)

parser.add_argument(
    "--noupdatealbummetadata",
    default=False,
    action='store_true',
    help="Disable the updating of album metadata"
)

parser.add_argument(
    "--allowDelete",
    type=convertAllowDelete,
    default="neither",
    help="Are we allowed to do delete operations: %s" %
    list(allowDeleteOptions)
)

parser.add_argument(
    "-r",
    "--replace",
    default=False,
    help="Replacement pattern. Search string is seperated by a pipe from "
    "replace string (ex: '-| '"
)

parser.add_argument(
    "-o",
    "--owner",
    default="default",
    help="The username of the user whos albums to sync (leave blank for your "
    "own)"
)

parser.add_argument(
    "--dateLimit",
    type=convertDate,
    help="A date limit, before which albums are ignored."
)

for comparison in Comparisons:
    parser.add_argument(
        "--override:%s" % comparison,
        default=None,
        help="Override the action for %s from the list of %s" %
        (comparison, ",".join(list(Actions)))
    )

args = parser.parse_args()

config = Config()

config.refreshLogin()

config.chosenFormats = args.format
config.dateLimit = args.dateLimit

config.verbose = args.verbose
config.rootDirs = args.directory  # set the directory you want to start from

config.albumNaming = args.naming
config.mode = args.mode
config.noupdatealbummetadata = args.noupdatealbummetadata
for comparison in Comparisons:
    r = getattr(args, "override:%s" % comparison, None)
    if r:
        mode[comparison] = r

config.excludes = r'|'.join([fnmatch.translate(x) for x in args.skip]) or r'$.'
config.server_excludes = \
r'|'.join([fnmatch.translate(x) for x in args.skipserver]) or r'$.'

print
(
    "Excluding %s on client and %s on server" %
    (config.excludes, config.server_excludes)
)

albums = Albums(
    config,
    args.replace,
    args.namingextract
)

albums.scanWebAlbums(
    args.owner,
    args.deletedups,
    config.server_excludes
)

albums.uploadMissingAlbumsAndFiles(
    args.compareattributes,
    config.mode,
    args.test,
    args.allowDelete
)

if args.purge:
    albums.deleteEmptyWebAlbums(args.owner)
