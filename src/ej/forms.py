from operator import attrgetter

from django.forms import Form, ModelForm, widgets
from django.utils.translation import gettext_lazy as _
from hyperpython import div, input_

NOT_GIVEN = object()


# TODO: move this functionality to Django-Boogie
class EjForm(Form):
    """
    Form with additional functionality.
    """

    def __init__(self, data=None, files=None, *args, request=None, **kwargs):
        if request is not None and request.method in self._meta_property(
            "http_methods", ("POST",)
        ):
            method = request.method
            data = getattr(request, method)
            kwargs.setdefault("files", request.FILES)
            super().__init__(data, *args, **kwargs)
            self.http_method = method
        else:
            super().__init__(data, *args, **kwargs)
            self.http_method = getattr(request, "method", None)

    def _meta_property(self, prop, default=NOT_GIVEN):
        try:
            return getattr(getattr(self, "Meta", None), prop)
        except AttributeError:
            if default is NOT_GIVEN:
                raise
            return default

    def is_valid_http(self, method):
        """
        Return true if form is valid and was submitted with the given HTTP
        method.

        Args:
            method (str or sequence): A string describing the method or a list
            of string
        """
        if self.http_method is None:
            msg = "must be initialized with a request to use this function"
            raise RuntimeError(msg)
        if (
            isinstance(method, str)
            and self.http_method == method.upper()
            or self.http_method in map(str.upper, method)
        ):
            return self.is_valid()
        else:
            return False

    def is_valid_post(self):
        return self.is_valid_http("POST")

    def is_valid_get(self):
        return self.is_valid_http("GET")

    def is_valid_put(self):
        return self.is_valid_http("PUT")

    def is_valid_patch(self):
        return self.is_valid_http("PATCH")

    def is_valid_delete(self):
        return self.is_valid_http("DELETE")

    def set_widget_attributes(self, attribute, value=None, from_attr=None):
        """
        Define the given attribute to all widgets in the form.
        """
        getter = from_attr and attrgetter(from_attr)
        for elem in self:
            if from_attr:
                value = getter(elem)
                elem.field.widget.attrs.setdefault(attribute, value)
            elif value is None:
                elem.field.widget.attrs.pop(attribute, None)
            else:
                elem.field.widget.attrs.setdefault(attribute, value)


class EjUserForm(EjForm):
    def __init__(self, *args, **kwargs):
        if "user" in kwargs:
            user = kwargs.pop("user")
        elif "request" in kwargs:
            user = kwargs["request"].user
        else:
            raise TypeError("User must be provided from request or user parameter")
        super().__init__(*args, **kwargs)
        self.user = user


class EjModelForm(EjForm, ModelForm):
    """
    A ModelForm version of the extended form.
    """

    def save(self, commit=True, **kwargs):
        instance = super().save(commit=False)
        for k, v in kwargs.items():
            setattr(instance, k, v)
        if commit:
            instance.save()
            self._save_m2m()
        return instance


class PlaceholderForm(EjForm):
    """
    Add placeholders from field labels.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_widget_attributes("placeholder", from_attr="label")


class FileInput(widgets.FileInput):
    """
    A custom file input widget used by all forms of ej.
    To specify witch type of file it will accept, pass 'accept'
    to attrs dict.
    E.g.: widgets.FileInput(attrs={'accept':'image/*'})
    """

    class Media:
        js = ("js/file-input.js",)

    def render(self, name, value, attrs=None, renderer=None):
        widget = self.get_context(name, value, attrs)["widget"]

        w_name = widget.get("name", "")
        w_type = widget.get("type", "")
        w_attrs = widget.get("attrs", {})

        return div(class_="FileInput")[
            div(class_="PickFileButton")[
                input_(style="opacity: 0", type_=w_type, name=w_name, **w_attrs),
                _("Choose a file"),
            ],
            div(class_="FileStatus")[_("No file chosen")],
        ].render()
