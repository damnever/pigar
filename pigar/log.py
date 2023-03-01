import logging

from .helpers import Color

_LOGGER_NAME = 'pigar'
logger = logging.getLogger(_LOGGER_NAME)


def enable_pretty_logging(log_level='info', with_others=False, logger=logger):
    logger.setLevel(getattr(logging, log_level.upper()))
    sh = logging.StreamHandler()
    sh.setFormatter(_LogFormatter())
    if not with_others:
        sh.addFilter(_LogFilter("pigar"))
    logger.addHandler(sh)


class _LogFormatter(logging.Formatter):

    FORMAT = '%(asctime)s %(message)s'
    DATE_FORMAT = '%H:%M:%S'
    DATE_COLOR = Color.BLUE
    LEVEL_COLORS = {
        logging.DEBUG: Color.NONE,
        logging.INFO: Color.GREEN,
        logging.WARNING: Color.YELLOW,
        logging.ERROR: Color.RED,
    }

    def __init__(
        self,
        fmt=FORMAT,
        datefmt=DATE_FORMAT,
        datecolor=DATE_COLOR,
        levelcolors=LEVEL_COLORS
    ):
        logging.Formatter.__init__(self, datefmt=datefmt)
        self._fmt = fmt

        self._datecolor = datecolor
        self._levelcolors = levelcolors

    def format(self, record: logging.LogRecord):
        record.asctime = self._datecolor(self.formatTime(record, self.datefmt))

        color = self._levelcolors.get(record.levelno, lambda x: x)
        message = color(record.getMessage())
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            message += '\n' + record.exc_text
        record.message = message

        formatted = self._fmt % record.__dict__
        return formatted.replace('\n', '\n    ')


class _LogFilter(logging.Filter):

    def filter(self, record: logging.LogRecord):
        return record.name == _LOGGER_NAME
