from django.db import models
from django.db.models.signals import pre_delete
import os
from django.contrib import admin
from django.conf import settings

class Uploads(models.Model):
    filename      = models.CharField(max_length=250, verbose_name='Filename')
    uuid          = models.CharField(unique=True, max_length=10, verbose_name='UUID')
    ext           = models.CharField(max_length=50, verbose_name="Extension")
    path          = models.CharField(max_length=250, verbose_name='Path')
    ip            = models.IPAddressField(verbose_name='IP Address')
    uploaded_on   = models.DateTimeField(auto_now=True, auto_now_add=True,\
                                        verbose_name='Uploaded On')
    views         = models.IntegerField(verbose_name='Views')
    size          = models.FloatField(verbose_name='Size')
    bandwidth     = models.FloatField(verbose_name='Bandwidth Used')
    source        = models.URLField(verbose_name='URL Source')
    filehash      = models.CharField(unique=True, max_length=250, verbose_name='Unique hash for the file')
    
    def __unicode__(self):
        return "%s.%s" % (self.uuid,self.ext)
        
    def view_image(self):
        return "%s/%s.%s" % (settings.SITE_URL,self.uuid,self.ext)

class UploadsAdmin(admin.ModelAdmin):
    list_display = ('view_image', 'ext', 'views', 'ip', 'uploaded_on','size', 'bandwidth','filehash', 'source')
    #list_filter = ('ip', 'source')
    search_fields = ('filename', 'uuid', 'ip', 'source', 'filehash')

def delete_upload(sender, **kwargs):
    """
    Creates a directory when the admin creates a group. The name of the directory
    is the same as the name of the group that was created.
    """
    instance = kwargs['instance']
    path_to_delete = '%s/%s.%s' % (instance.path,instance.uuid,instance.ext)
    if not os.path.isdir(path_to_delete):
        os.unlink(path_to_delete)
        
pre_delete.connect(delete_upload, sender=Uploads)
admin.site.register(Uploads,UploadsAdmin)