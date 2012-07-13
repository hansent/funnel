import base64
import tempfile
import StringIO

from boto import s3
from boto.s3.connection import S3Connection

class S3BucketMixin(object):
    s3_bucket =  None
    def get_s3_bucket(self):
        s3_bucket = self.s3_bucket or self.settings.get("s3_bucket")
        s3_id = self.settings.get("s3_id")
        s3_key = self.settings.get("s3_key")
        conn = S3Connection(s3_id, s3_key)
        return conn.get_bucket(s3_bucket)

    def s3_write_dataurl(self, data_url, **kwargs):
        header, data = data_url.split(',')
        mimetype = header.split(':')[1].split(';')[0] #ignore 'data:' prefix
        tmpfile = tempfile.TemporaryFile()
        tmpfile.write(base64.b64decode(data))
        tmpfile.seek(0)
        key_name = self.s3_write_file(tmpfile, mimetype, **kwargs)
        tmpfile.close()
        return key_name

    def s3_write_file(self, fp, mimetype="image/png", **kwargs):
        k = s3.key.Key(self.get_s3_bucket())
        md5 = k.compute_md5(fp)
        k.name = "%s.%s" % (md5[0] , mimetype.split('/')[1])
        k.set_metadata('Content-Type', mimetype)
        k.set_contents_from_file(fp, md5=md5)
        k.make_public()
        return k.name

    def s3_open_file(self, file_name, **kwargs):
        k = s3.key.Key(self.get_s3_bucket(), file_name)
        fp = StringIO.StringIO()
        k.get_file(fp)
        fp.seek(0)
        return fp
