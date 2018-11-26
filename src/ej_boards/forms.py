from django import forms

from . import models

class BoardForm(forms.ModelForm):
    class Meta:
        model = models.Board
        fields = ['slug', 'title', 'description', 'palette']
        widgets = { 'palette': forms.RadioSelect }
