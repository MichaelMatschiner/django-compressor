import fnmatch
import os
from optparse import make_option

from django.core.cache import cache
from django.core.management.base import NoArgsCommand, CommandError

from compressor.conf import settings
from compressor.utils import get_mtime, get_mtime_cachekey

class Command(NoArgsCommand):
    help = "Add or remove all mtime values from the cache"
    option_list = NoArgsCommand.option_list + (
        make_option('-i', '--ignore', action='append', default=[],
            dest='ignore_patterns', metavar='PATTERN',
            help="Ignore files or directories matching this glob-style "
                "pattern. Use multiple times to ignore more."),
        make_option('--no-default-ignore', action='store_false',
            dest='use_default_ignore_patterns', default=True,
            help="Don't ignore the common private glob-style patterns 'CVS', "
                "'.*' and '*~'."),
        make_option('--follow-links', dest='follow_links', action='store_true',
            help="Follow symlinks when traversing the COMPRESS_ROOT "
                "(which defaults to MEDIA_ROOT). Be aware that using this "
                "can lead to infinite recursion if a link points to a parent "
                "directory of itself."),
        make_option('-c', '--clean', dest='clean', action='store_true',
            help="Remove all items"),
        make_option('-a', '--add', dest='add', action='store_true',
            help="Add all items"),
    )

    def is_ignored(self, path):
        """
        Return True or False depending on whether the ``path`` should be
        ignored (if it matches any pattern in ``ignore_patterns``).
        """
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatchcase(path, pattern):
                return True
        return False

    def handle_noargs(self, **options):
        ignore_patterns = options['ignore_patterns']
        if options['use_default_ignore_patterns']:
            ignore_patterns += ['CVS', '.*', '*~']
            options['ignore_patterns'] = ignore_patterns
        self.ignore_patterns = ignore_patterns

        if (options['add'] and options['clean']) or (not options['add'] and not options['clean']):
            raise CommandError('Please specify either "--add" or "--clean"')

        added_files = 0
        for root, dirs, files in os.walk(settings.MEDIA_ROOT, followlinks=options['follow_links']):
            for dir_ in dirs:
                if self.is_ignored(dir_):
                    dirs.remove(dir_)
            for filename in files:
                common = "".join(root.split(settings.MEDIA_ROOT))
                if common.startswith(os.sep):
                    common = common[len(os.sep):]
                if self.is_ignored(os.path.join(common, filename)):
                    continue
                filename = os.path.join(root, filename)
                cache.delete(get_mtime_cachekey(filename))
                if options['add']:
                    added_files += 1
                    get_mtime(filename)
        if added_files:
            print "Added mtimes of %d files to cache." % added_files
