
supportedImageFormats = frozenset(
    [
        "image/bmp",
        "image/gif",
        "image/jpeg",
        "image/png"
    ]
)

supportedVideoFormats = frozenset(
    [
        "video/3gpp",
        "video/avi",
        "video/quicktime",
        "video/mp4",
        "video/mpeg",
        "video/mpeg4",
        "video/msvideo",
        "video/x-ms-asf",
        "video/x-ms-wmv",
        "video/x-msvideo"
    ]
)


class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError


Comparisons = Enum(
    [
        'REMOTE_OLDER',
        'DIFFERENT',
        'SAME',
        'UNKNOWN',
        'LOCAL_ONLY',
        'REMOTE_ONLY'
    ]
)

Actions = Enum(
    [
        'UPLOAD_LOCAL',
        'DELETE_LOCAL',
        'SILENT',
        'REPORT',
        'DOWNLOAD_REMOTE',
        'DELETE_REMOTE',
        'TAG_REMOTE',
        'REPLACE_REMOTE_WITH_LOCAL',
        'UPDATE_REMOTE_METADATA'
    ]
)

UploadOnlyActions = {
    Comparisons.REMOTE_OLDER: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.DIFFERENT: Actions.REPORT,
    Comparisons.SAME: Actions.SILENT,
    Comparisons.UNKNOWN: Actions.REPORT,
    Comparisons.LOCAL_ONLY: Actions.UPLOAD_LOCAL,
    Comparisons.REMOTE_ONLY: Actions.REPORT}
DownloadOnlyActions = {
    Comparisons.REMOTE_OLDER: Actions.REPORT,
    Comparisons.DIFFERENT: Actions.DOWNLOAD_REMOTE,
    Comparisons.SAME: Actions.SILENT,
    Comparisons.UNKNOWN: Actions.REPORT,
    Comparisons.LOCAL_ONLY: Actions.REPORT,
    Comparisons.REMOTE_ONLY: Actions.DOWNLOAD_REMOTE}
PassiveActions = {
    Comparisons.REMOTE_OLDER: Actions.REPORT,
    Comparisons.DIFFERENT: Actions.REPORT,
    Comparisons.SAME: Actions.SILENT,
    Comparisons.UNKNOWN: Actions.REPORT,
    Comparisons.LOCAL_ONLY: Actions.REPORT,
    Comparisons.REMOTE_ONLY: Actions.REPORT}
RepairActions = {
    Comparisons.REMOTE_OLDER: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.DIFFERENT: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.SAME: Actions.SILENT,
    Comparisons.UNKNOWN: Actions.UPDATE_REMOTE_METADATA,
    Comparisons.LOCAL_ONLY: Actions.UPLOAD_LOCAL,
    Comparisons.REMOTE_ONLY: Actions.DELETE_REMOTE}
SyncActions = {
    Comparisons.REMOTE_OLDER: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.DIFFERENT: Actions.REPORT,
    Comparisons.SAME: Actions.SILENT,
    Comparisons.UNKNOWN: Actions.REPORT,
    Comparisons.LOCAL_ONLY: Actions.UPLOAD_LOCAL,
    Comparisons.REMOTE_ONLY: Actions.DOWNLOAD_REMOTE}
SyncUploadActions = {
    Comparisons.REMOTE_OLDER: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.DIFFERENT: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.SAME: Actions.SILENT,
    Comparisons.UNKNOWN: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.LOCAL_ONLY: Actions.UPLOAD_LOCAL,
    Comparisons.REMOTE_ONLY: Actions.DELETE_REMOTE}

modes={
    'upload': UploadOnlyActions,
    'download': DownloadOnlyActions,
    'report': PassiveActions,
    'repairUpload': RepairActions,
    'sync': SyncActions,
    'syncUpload': SyncUploadActions
}

formats={
    'photo': supportedImageFormats,
    'video': supportedVideoFormats,
    'both': supportedImageFormats.union(supportedVideoFormats)
}

allowDeleteOptions={
    'neither': (False, False),
    'both': (True, True),
    'local': (True, False),
    'remote': (False, True)
}


def convertAllowDelete(string):
    return allowDeleteOptions[string]


def convertMode(string):
    return modes[string]


def convertFormat(string):
    return formats[string]


def convertDate(string):
    return time.strptime(string, '%Y-%m-%d')


defaultNamingFormat = ["{0}", "{1} ({0})"]
