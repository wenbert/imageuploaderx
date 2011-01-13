from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from upload.forms import *
from django.core.context_processors import csrf
from django.template import RequestContext
import os.path
from django.contrib import messages
import uuid
from django.conf import settings
from upload.models import *
import mimetypes
from django.http import HttpResponse, Http404
from django.utils.encoding import smart_str
import datetime
import random
import base64
import cStringIO # *much* faster than StringIO
import urllib
import Image
import time
import hashlib 
import shutil

def upload(request, uuid=None):
    viewdate = ''
    #if 'uploadedfiles' not in request.session:
    #    request.session['uploadedfiles'] = ""
    
    if request.method == 'POST':
        
        if 'url' not in request.POST:
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                uuid = handle_uploaded_file(request)
                response = HttpResponseRedirect(uuid)
                
                if 'uploadedfiles' in request.session:
                    request.session['uploadedfiles'] += " " + str(uuid)
                else:
                    request.session['uploadedfiles'] = str(uuid)
                
                return response
        else:
            formurl = UploadURLForm(request.POST)
            if formurl.is_valid():
                uuid = handle_url_file(request)
                response = HttpResponseRedirect(uuid)
                
                if 'uploadedfiles' in request.session:
                    request.session['uploadedfiles'] += " " + str(uuid)
                else:
                    request.session['uploadedfiles'] = str(uuid)
                    
                return response
    else:
        form = UploadFileForm()
        formurl = UploadURLForm()
    
    if uuid:
        image = Uploads.objects.get(uuid=uuid)
        viewdate = pretty_date(int(time.mktime(time.strptime(str(image.uploaded_on), '%Y-%m-%d %H:%M:%S'))))
        
        data = RequestContext(request, {
            'uuid': image.uuid,
            'ext': str(image.ext).lower(),
            'path': image.path,
            'uploaded_on': viewdate,
            'views': image.views,
            'url': settings.SITE_URL,
            'cookies': request.COOKIES,
            'session':request.session,
            'filehash':image.filehash,
            'size': convert_bytes(image.size),
            'bandwidth': convert_bytes(image.bandwidth),
        })
        
        response = render_to_response('upload/upload.html', data)
        
        if request.session.get('has_visited', False):
            pass
        else:
            request.session['has_visited'] = True
            image.views += 1
            
        image.bandwidth += image.size
        image.save()
        
        return response        
    else:
        form = RequestContext(request, {
            'form': form,
            'formurl': formurl,
        })
        return render_to_response('upload/upload.html', form)    
    
def handle_uploaded_file(request):
    
    f = request.FILES['file']
    ext = str(f).split('.')[-1]
    #ext = os.path.splitext(f)[1]
    
    #filename = "%s.%s" % (uuid.uuid4(), ext)
    randname = rand1(settings.RANDOM_ID_LENGTH)
    filename = "%s.%s" % (randname, ext)
    
    file_path_destination = os.path.join(settings.UPLOAD_DIRECTORY,filename)
    
    filehash = None
    destination = None
    uuid = None
    
    #no more checking of file hash
    #filehash = checkhash(f)
    destination = open(file_path_destination, 'wb+')
    for chunk in f.chunks():
        destination.write(chunk)
    destination.close()
    
    upload = Uploads(
        ip          = request.META['REMOTE_ADDR'],
        filename    = f.name,
        uuid        = randname,
        ext         = ext,
        path        = settings.UPLOAD_DIRECTORY,
        views       = 1,
        source      = "-",
        size        = f.size,
        bandwidth   = f.size,
        filehash    = '',
    )
    upload.save()
    return "%s" % (upload.uuid)
    
        
        
def handle_url_file(request):
    """
    Open a file from a URL.
    Split the file to get the filename and extension.
    Generate a random uuid using rand1()
    Then save the file.
    Return the UUID when successful.
    """
    
    randname = rand1(settings.RANDOM_ID_LENGTH)
    url = request.POST['url'].split('?')[0]
    filename = os.path.basename(url)
    ext = os.path.splitext(filename)[1]
    #ext = os.path.splitext(filename)[1].replace(".", "")
    path = os.path.join(settings.UPLOAD_DIRECTORY, randname)

    f = urllib.urlopen(request.POST['url'])
    p = os.path.join(settings.UPLOAD_DIRECTORY, randname + ext)
    filesize = 0
    with open(p,'wb') as output:
        while True:
            buf = f.read(65536)
            filesize += len(buf)
            if not buf:
                break
            output.write(buf)
    #filesize = len(f.read())
    
    upload = Uploads(
        ip          = request.META['REMOTE_ADDR'],
        filename    = filename,
        uuid        = randname,
        ext         = ext.replace(".", ""),
        path        = settings.UPLOAD_DIRECTORY,
        views       = 1,
        bandwidth   = filesize,
        source      = request.POST['url'],
        size        = filesize,
        filehash    = '',
    )

    upload.save()
    return upload.uuid
   

def raw(request,uuid):
    target = str(uuid).split('.')[:-1][0]
    image = Uploads.objects.get(uuid=target)
    
    path = image.path
    filepath = os.path.join(path,"%s.%s" % (image.uuid,image.ext))
    
    """
    #Allow for hot-linking
    if 'HTTP_REFERER' in request.META:
        if settings.REFERER not in request.META['HTTP_REFERER']:
            return render_to_response('403.html')
        else:
            pass
    else:
        return render_to_response('403.html')        
    """
        
    response = HttpResponse(mimetype=mimetypes.guess_type(filepath)) 
    response['Content-Disposition']='filename="%s"'\
                                    %smart_str(image.filename)
    response["X-Sendfile"] = filepath
    response['Content-length'] = os.stat(filepath).st_size

    return response


def options(request,uuid):
    """
    This is for the Image Option page.
    """
    image = Uploads.objects.get(uuid=uuid)
    allow_delete = None
    if 'uploadedfiles' in request.session:
        if image.uuid in request.session['uploadedfiles']:
            allow_delete = 'yes'
            #form = DeleteImageForm(uuid)
        else:
            allow_delete = 'no'
            #form = None
    else:
        pass
    
    data = RequestContext(request, {
        'uuid': image.uuid,
        'ext': image.ext,
        'path': image.path,
        'uploaded_on': image.uploaded_on,
        'views': image.views,
        'url': settings.SITE_URL,
        'cookies': request.COOKIES,
        'allow_delete': allow_delete,
        'email':settings.IMAGE_DELETION_EMAIL,
        'email_label':settings.IMAGE_DELETION_EMAIL_LABEL,
        #'form': form,
    })
    
    return render_to_response('upload/options.html', data)

def delete(request,uuid):
    """
    Permanently deletes a file
    """
    try:
        image = Uploads.objects.get(uuid=uuid)
        
        if 'uploadedfiles' in request.session:
            if str(image.uuid) in request.session['uploadedfiles']:
                image.delete()
            else:
                return render_to_response('403.html')
        else:
            return render_to_response('403.html')
            
        data = RequestContext(request, {
            'uuid': uuid
        })
        return render_to_response('upload/delete.html', data)

    except NameError, e:
        raise e


        
def checkhash(f, block_size=8192):
    """
    Check hash of the file then return it.
    http://stackoverflow.com/questions/1131220/get-md5-hash-of-a-files-without-open-it-in-python
    """
    md5 = hashlib.md5()
    while True:
        data = f.read(block_size)
        if not data:
            break
        md5.update(data)
    #return md5.digest()
    return md5.hexdigest()
        
def rand1(leng):
    """
    http://stackoverflow.com/questions/785058/random-strings-in-python-2-6-is-this-ok
    """
    nbits = leng * 6 + 1
    bits = random.getrandbits(nbits)
    uc = u"%0x" % bits
    newlen = int(len(uc) / 2) * 2 # we have to make the string an even length
    ba = bytearray.fromhex(uc[:newlen])
    return str(base64.urlsafe_b64encode(str(ba))[:leng]).replace("-","_")
    
def set_cookie(response, key, value, days_expire = 7):
    """
    http://stackoverflow.com/questions/1622793/django-cookies-how-can-i-set-them/1623910#1623910
    """
    if days_expire is None:
        max_age = 365*24*60*60  #one year
    else:
        max_age = days_expire*24*60*60 
    expires = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=max_age), "%a, %d-%b-%Y %H:%M:%S GMT")
    response.set_cookie(key, value, max_age=max_age, expires=expires, domain=settings.SESSION_COOKIE_DOMAIN, secure=settings.SESSION_COOKIE_SECURE or None)
    return response
    
def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    http://stackoverflow.com/questions/1551382/python-user-friendly-time-format
    """
    from datetime import datetime
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif not time:
        diff = now - now
    else:
        diff = now - datetime.fromtimestamp(time)
        
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " second(s) ago"
        if second_diff < 120:
            return  "a minute ago"
        if second_diff < 3600:
            return str( second_diff / 60 ) + " minute(s) ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str( second_diff / 3600 ) + " hour(s) ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " day(s) ago"
    if day_diff < 31:
        return str(day_diff/7) + " week(s) ago"
    if day_diff < 365:
        return str(day_diff/30) + " month(s) ago"
    return str(day_diff/365) + " year(s) ago"

def convert_bytes(bytes):
    """
    Convert file sizes to human readable ones.
    I forgot to credit the author of this code. I forgot where I found it.
    If you know, then please email me. wenbert[at]gmail[dot]com
    """
    bytes = float(bytes)
    if bytes >= 1099511627776:
        terabytes = bytes / 1099511627776
        size = '%.2f Tb' % terabytes
    elif bytes >= 1073741824:
        gigabytes = bytes / 1073741824
        size = '%.2f Gb' % gigabytes
    elif bytes >= 1048576:
        megabytes = bytes / 1048576
        size = '%.2f Mb' % megabytes
    elif bytes >= 1024:
        kilobytes = bytes / 1024
        size = '%.2f Kb' % kilobytes
    else:
        size = '%.2f bytes' % bytes
    return size
    
def checkhash(f, block_size=8192):
    """
    Check hash of the file then return it.
    http://stackoverflow.com/questions/1131220/get-md5-hash-of-a-files-without-open-it-in-python
    """
    md5 = hashlib.md5()
    while True:
        data = f.read(block_size)
        if not data:
            break
        md5.update(data)
    #return md5.digest()
    return md5.hexdigest()
    
def clearsession(request):
    try:
        del request.session['uploadedfiles']
        del request.session['upload_list']
        del request.session
        request.session.delete('upload_list') 
    except KeyError:
        pass
    return HttpResponse("Session cleared.")
    
class ImageSequence:
    def __init__(self, im):
        self.im = im
    def __getitem__(self, ix):
        try:
            if ix:
                self.im.seek(ix)
            return self.im
        except EOFError:
            #raise IndexError # end of sequence
            pass