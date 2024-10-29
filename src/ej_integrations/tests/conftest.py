import pytest
from ej_conversations.tests.conftest import *
from ej_integrations.models import OpinionComponent


@pytest.fixture
def opinion_component(db, conversation):
    instance = OpinionComponent()
    instance.conversation = conversation
    instance.final_voting_message = "texto final de votação"
    instance.save()
    return instance
