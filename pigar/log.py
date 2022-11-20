import logging
import logging.handlers

from .helpers import Color

logger = logging.getLogger('pigar')


def enable_pretty_logging(log_level='info', logger=logger):
    logger.setLevel(getattr(logging, log_level.upper()))
    sh = logging.StreamHandler()
    sh.setFormatter(_LogFormatter())
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

    def format(self, record):
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
