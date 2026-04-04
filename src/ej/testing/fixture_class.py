import functools

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from model_mommy.recipe import Recipe
from sidekick import record

User = get_user_model()


def named_fixture(name):
    def decorator(func):
        fixture = pytest.fixture(name=name)(func)
        fixture.__name__ = fixture.__qualname__ = name
        fixture.implementation_function = func
        return fixture

    return decorator


class FixtureMeta(type):
    def __init__(cls, clsname, bases, ns):  # noqa: N805
        super().__init__(clsname, bases, ns)
        cls._fixtures = dict(getattr(cls, "_fixtures", {}))
        cls._recipes = dict(getattr(cls, "_recipes", {}))

        for name, recipe in ns.items():
            if isinstance(recipe, Recipe):
                ns = make_recipe(name, recipe)
                for k, v in ns.items():
                    setattr(cls, k, fixture_method(v))
                cls._fixtures.update(ns)
                cls._recipes[name] = recipe

    def update_globals(cls, globals):  # noqa: N805
        globals.update(cls._fixtures)
        globals.update(cls._recipes)


def make_recipe(name, recipe):
    @named_fixture(name=name)
    def fixture_function():
        return recipe.prepare()

    @named_fixture(name=name + "_db")
    def fixture_function_db(db):
        return recipe.make()

    @named_fixture(name=name + "_rec")
    def fixture_function_rec():
        return recipe

    @named_fixture(name="mk_" + name)
    def fixture_function_mk(db):
        return recipe.make

    @named_fixture(name="prep_" + name)
    def fixture_function_prep():
        return recipe.prepare

    fixture_map = {
        "fixture_" + name: fixture_function,
        "fixture_" + name + "_db": fixture_function_db,
        "fixture_" + name + "_recipe": fixture_function_rec,
        "fixture_mk_" + name: fixture_function_mk,
        "fixture_prep_" + name: fixture_function_prep,
    }
    recipe.fixture_map = fixture_map
    return fixture_map


def fixture_method(fixture):
    name = fixture.__name__
    func = fixture.implementation_function

    if name.endswith("_db") or name.startswith("mk_"):

        @named_fixture(name)
        def method(self, db):
            return func(db)

    else:

        @named_fixture(name)
        def method(self):
            return func()

    return method


def wraps(func):
    @functools.wraps(func)
    def method(self, *args, **kwargs):
        try:
            testcase = self._testcase
        except AttributeError:
            testcase = self._testcase = TestCase()
        return func(testcase, *args, **kwargs)

    return method


class EjRecipes(metaclass=FixtureMeta):
    """
    Base recipes for the site
    """

    user = Recipe(
        User, is_superuser=False, email="user@domain.com", name="user"
    )
    author = Recipe(
        User, is_superuser=False, email="author@domain.com", name="author"
    )
    root = Recipe(
        User,
        is_superuser=True,
        email="root@domain.com",
        is_staff=True,
        name="root",
    )
    admin = Recipe(
        User,
        is_superuser=True,
        email="admin@domain.com",
        is_staff=True,
        name="admin",
    )

    @pytest.fixture
    def anonymous_user(self):
        return AnonymousUser()

    @pytest.fixture
    def user_client(self, client, user_db):
        client.force_login(user_db)
        yield client
        user_db.delete()

    @pytest.fixture
    def author_client(self, client, author_db):
        client.force_login(author_db)
        yield client
        author_db.delete()

    @pytest.fixture
    def admin_client(self, client, root_db):
        client.force_login(root_db)
        yield client
        root_db.delete()

    @pytest.fixture
    def data(self, request):
        self.get_fixture("db", request)
        return self.get_data(request)

    def get_data(self, request):
        user, author, admin = self.get_users(request)
        return record(user=user, author=author, admin=admin)

    def get_users(self, request):
        user = self.get_fixture("user_db", request)
        author = self.get_fixture("author_db", request)
        admin = self.get_fixture("admin_db", request)
        return user, author, admin

    def get_fixture(self, fixture, request):
        return request.getfixturevalue(fixture)

    # Settings
    settings = TestCase.settings
    modify_settings = TestCase.modify_settings

    assert_redirects = wraps(TestCase.assertRedirects)
    assert_contains = wraps(TestCase.assertContains)
    assert_not_contains = wraps(TestCase.assertNotContains)
    assert_form_error = wraps(TestCase.assertFormError)
    assert_formset_error = wraps(TestCase.assertFormSetError)
    assert_template_used = wraps(TestCase.assertTemplateUsed)
    assert_template_not_used = wraps(TestCase.assertTemplateNotUsed)
    assert_raises_message = wraps(TestCase.assertRaisesMessage)
    assert_warns_message = wraps(TestCase.assertWarnsMessage)
    assert_field_output = wraps(TestCase.assertFieldOutput)
    assert_html_equal = wraps(TestCase.assertHTMLEqual)
    assert_html_not_equal = wraps(TestCase.assertHTMLNotEqual)
    assert_in_html = wraps(TestCase.assertInHTML)
    assert_json_equal = wraps(TestCase.assertJSONEqual)
    assert_json_not_equal = wraps(TestCase.assertJSONNotEqual)
    assert_xml_equal = wraps(TestCase.assertXMLEqual)
    assert_xml_not_equal = wraps(TestCase.assertXMLNotEqual)

    sub_test = TestCase.subTest
