from django import forms

class UploadFileForm(forms.Form):
    file  = forms.ImageField()
    #nsfw_file = forms.BooleanField(required=False,label="NSFW, Nudity, Explicit Language? ")
    
class UploadURLForm(forms.Form):
    url = forms.URLField(widget=forms.TextInput(attrs={'class':'linkbox'}))
    
    #nsfw_url = forms.BooleanField(required=False,label="NSFW, Nudity, Explicit Language? ")
    
    