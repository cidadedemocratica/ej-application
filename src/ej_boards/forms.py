import django
from django.forms.renderers import TemplatesSetting
from django import forms

from . import models
from ej.utils.widgets import FileInput

class PaletteWidget(forms.RadioSelect):
  template_name = 'forms/templates/radio.html'
  def render(self, name, value, attrs, renderer):
        context = self.get_context(name, value, attrs)
        renderer = TemplatesSetting()
        return renderer.render(self.template_name, context)

class BoardForm(forms.ModelForm):
    class Meta:
        model = models.Board
        fields = ['slug', 'title', 'description', 'palette', 'image']
        widgets = { 'palette': PaletteWidget, 'image': FileInput }
