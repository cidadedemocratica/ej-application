from ej.forms import EjModelForm
from .models import RasaConversation

class RasaConversationForm(EjModelForm):
    class Meta:
        model = RasaConversation
        fields = ["conversation", "domain"]
        help_texts = {"conversation": None, "domain": None}

    def __init__(self, *args, conversation, **kwargs):
        kwargs.update(initial={
        'conversation': conversation
        })
        super(RasaConversationForm, self).__init__(*args, **kwargs)