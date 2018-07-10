import pytest

from django.utils.translation import ugettext as _

from ej_profiles.choices import Gender, Race
from ej_profiles.models import Profile
from ej_users.models import User


class TestProfile:
    @pytest.fixture
    def profile(self):
        return Profile(
            user=User(username='user', name='name'),
            image='image',
            age=18,
            phone='phone',
            country='country',
            city='city',
            state='state',
            biography='biography',
            occupation='occupation',
            gender=Gender.FEMALE,
            political_activity='political_activity',
            race=Race.INDIGENOUS,
        )

    def test_profile_invariants(self, profile):
        assert str(profile) == 'name\'s profile'
        assert profile.is_filled
        assert profile.profile_fields() == [
            ('City', 'city'),
            ('Country', 'country'),
            ('Occupation', 'occupation'),
            ('Age', 18),
            ('Phone', "61999999999"),
            ('Gender identity', 'female'),
            ('Race', 'indigenous'),
            ('Political activity', 'political_activity'),
            ('Biography', 'biography'),
        ]
        assert profile.statistics() == {'votes': 0, 'comments': 0, 'conversations': 0}
        assert profile.role() == _('Regular user')

        # Remove a field
        profile.occupation = ''
        assert not profile.is_filled
