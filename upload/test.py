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

def upload(request, uuid=None):
    
    if 'uploadedfiles' not in request.session:
        request.session['uploadedfiles'] = ""
    
    if request.method == 'POST':
        
        if 'url' not in request.POST:
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                
                uuid = handle_uploaded_file(request)
                messages.success(request, 'Successful upload!')
                
                #set uuid in cookie
                response = HttpResponseRedirect(uuid)
                """
                upload_images = ""
                if 'uploaded_images' in request.COOKIES:
                    upload_images = request.COOKIES['uploaded_images'] + " " + str(uuid)
                set_cookie(response, 'uploaded_images', upload_images)
                """
                if 'uploadedfiles' in request.session:
                    request.session['uploadedfiles'] += " " + str(uuid)
                else:
                    request.session['uploadedfiles'] = str(uuid)

                
                return response
        else:
            formurl = UploadURLForm(request.POST)
            if formurl.is_valid():
                
                uuid = handle_url_file(request)
                messages.success(request, 'Successful upload!')
                
                #set uuid in cookie
                response = HttpResponseRedirect(uuid)
                """
                upload_images = ""
                if 'uploaded_images' in request.COOKIES:
                    upload_images = request.COOKIES['uploaded_images'] + " " + str(uuid)
                set_cookie(response, 'uploaded_images', upload_images)
                """
                if 'uploadedfiles' in request.session:
                    request.session['uploadedfiles'] += " " + str(uuid)
                else:
                    request.session['uploadedfiles'] = str(uuid)
                
                return response
    else:
        form = UploadFileForm()
        formurl = UploadURLForm()
        
    

    #request.session['uploaded_files'].append(str(uuid))
                    
    if uuid:
        image = Uploads.objects.get(uuid=uuid)
        
        data = RequestContext(request, {
            'uuid': image.uuid,
            'ext': str(image.ext).lower(),
            'path': image.path,
            'uploaded_on': image.uploaded_on,
            'views': image.views,
            'url': settings.SITE_URL,
            'cookies': request.COOKIES,
            'sessionid': request.session.session_key,
            'session':request.session,
            #'sessionid': request.COOKIES[settings.SESSION_COOKIE_NAME],
        })
        
        response = render_to_response('upload/upload.html', data)
        
        """
        if image.uuid not in request.COOKIES['uploaded_images']:
            image.views += 1
            image.save()
        else:
            pass
        """
        if image.uuid not in request.session['uploadedfiles']:
            image.views += 1
            image.save()
        else:
            pass
            
        return response        
    else:
        form = RequestContext(request, {
            'form': form,
            'formurl': formurl,
        })
        return render_to_response('upload/upload.html', form)

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
    
    if image.uuid in request.session['uploadedfiles']:
        allow_delete = 'yes'
        #form = DeleteImageForm(uuid)
    else:
        allow_delete = 'no'
        #form = None
    
    data = RequestContext(request, {
        'uuid': image.uuid,
        'ext': image.ext,
        'path': image.path,
        'uploaded_on': image.uploaded_on,
        'views': image.views,
        'url': settings.SITE_URL,
        'cookies': request.COOKIES,
        'allow_delete': allow_delete,
        #'form': form,
    })
    
    return render_to_response('upload/options.html', data)
    
def delete(request,uuid):
    """
    Permanently deletes a file
    """
    try:
        """
        formurl = UploadURLForm(request.POST)
        if formurl.is_valid():
            image = Uploads.objects.get(uuid=request.POST['uuid'])
            os.unlink(os.path.join(image.path,"%s.%s" % (image.uuid,image.ext)))
            image.delete()    
        """
        image = Uploads.objects.get(uuid=uuid)
        
        if 'uploadedfiles' in request.session:
            if str(image.uuid) in request.session['uploadedfiles']:
                os.unlink(os.path.join(image.path,"%s.%s" % (image.uuid,image.ext)))
                image.delete()
            else:
                return render_to_response('403.html')
        else:
            pass
            
        data = RequestContext(request, {
            'uuid': uuid
        })
        return render_to_response('upload/delete.html', data)

    except NameError, e:
        raise e
    
def handle_uploaded_file(request):
    try:
        f = request.FILES['file']
        ext = str(f).split('.')[-1]
        
        #filename = "%s.%s" % (uuid.uuid4(), ext)
        randname = rand1(5)
        filename = "%s.%s" % (randname, ext)
        
        if 'nsfw_file' in request.POST:
            nsfw_file = 1
        else:
            nsfw_file = 0
        
        upload = Uploads(
            ip          = request.META['REMOTE_ADDR'],
            filename    = f.name,
            uuid        = randname,
            ext         = ext,
            path        = settings.UPLOAD_DIRECTORY,
            views       = 1,
            nsfw        = nsfw_file,
            source      = "-",
        )
            
        upload.save()
        
        file_path_destination = os.path.join(settings.UPLOAD_DIRECTORY,filename)
        destination = open(file_path_destination, 'wb+')
        for chunk in f.chunks():
            destination.write(chunk)
        destination.close()
        
        return "%s" % (upload.uuid)
        
    except NameError, e:
        raise e
        
def handle_url_file(request):
    """
    Open a file from a URL.
    Split the file to get the filename and extension.
    Generate a random uuid using rand1()
    Then save the file.
    Return the UUID when successful.
    """
    try:
        file = urllib.urlopen(request.POST['url'])
        randname = rand1(5)
        newfilename = request.POST['url'].split('/')[-1]
        ext = str(newfilename.split('.')[-1]).lower()
        im = cStringIO.StringIO(file.read()) # constructs a StringIO holding the image
        img = Image.open(im)
        img.save(os.path.join(settings.UPLOAD_DIRECTORY,(("%s.%s")%(randname,ext))))
        del img
        
        if 'nsfw_url' in request.POST:
            nsfw_url = 1
        else:
            nsfw_url = 0
        
        upload = Uploads(
            ip          = request.META['REMOTE_ADDR'],
            filename    = newfilename,
            uuid        = randname,
            ext         = ext,
            path        = settings.UPLOAD_DIRECTORY,
            views       = 1,
            nsfw        = nsfw_url,
            source      = request.POST['url'],
        )
            
        upload.save()
        #return uuid
        return "%s" % (upload.uuid)
    except IOError, e:
        raise e
        
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
