import os


class ConstanceConf:
    """
    Dynamic django settings, edit on admin page
    """

    CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"
    CONSTANCE_IGNORE_ADMIN_VERSION_CHECK = True

    def get_constance_config(self):
        return {
            "EJ_MAX_BOARD_NUMBER": (
                self.EJ_MAX_BOARD_NUMBER,
                "Maximum number of boards that a common user can create",
                int,
            ),
            "EJ_LISTEN_TO_COMMUNITY_SIGNATURE_CONVERSATIONS_LIMIT": (
                self.EJ_LISTEN_TO_COMMUNITY_SIGNATURE_CONVERSATIONS_LIMIT,
                "Maximum number of conversations that a common user can create if they have Listen to Community signature.",
                int,
            ),
            "EJ_LISTEN_TO_COMMUNITY_SIGNATURE_VOTE_LIMIT": (
                self.EJ_LISTEN_TO_COMMUNITY_SIGNATURE_VOTE_LIMIT,
                "Maximum number of votes that a common user can give if they have Listen to Community signature.",
                int,
            ),
            "EJ_LISTEN_TO_CITY_SIGNATURE_CONVERSATIONS_LIMIT": (
                self.EJ_LISTEN_TO_CITY_SIGNATURE_CONVERSATIONS_LIMIT,
                "Maximum number of conversations that a common user can create if they have Listen to City signature.",
                int,
            ),
            "EJ_LISTEN_TO_CITY_SIGNATURE_VOTE_LIMIT": (
                self.EJ_LISTEN_TO_CITY_SIGNATURE_VOTE_LIMIT,
                "Maximum number of votes that a common user can give if they have Listen to City signature.",
                int,
            ),
            "EJ_LISTEN_TO_CITY_YEARLY_SIGNATURE_CONVERSATIONS_LIMIT": (
                self.EJ_LISTEN_TO_CITY_YEARLY_SIGNATURE_CONVERSATIONS_LIMIT,
                "Maximum number of conversations that a common user can create if they have Listen to City yearly signature.",
                int,
            ),
            "EJ_LISTEN_TO_CITY_YEARLY_SIGNATURE_VOTE_LIMIT": (
                self.EJ_LISTEN_TO_CITY_YEARLY_SIGNATURE_VOTE_LIMIT,
                "Maximum number of votes that a common user can give if they have Listen to City yearly signature.",
                int,
            ),
            "EJ_PROFILE_STATE_CHOICES": (
                self.EJ_PROFILE_STATE_CHOICES,
                "State choices for state field in profile",
                "choicesfield",
            ),
            "EJ_LANDING_PAGE_DOMAIN": (
                self.EJ_LANDING_PAGE_DOMAIN,
                "Redirect url for when the user is not logged in to the platform",
                "charfield",
            ),
            "RETURN_USER_SKIPED_COMMENTS": (
                self.RETURN_USER_SKIPED_COMMENTS,
                "Set this variable to 'False' if you don't want users to vote again on comments they already skipped.",
                bool,
            ),
        }

    CONSTANCE_ADDITIONAL_FIELDS = {
        "charfield": [
            "django.forms.fields.CharField",
            {"widget": "django.forms.TextInput", "required": False},
        ],
        "choicesfield": ["django.forms.ChoiceField", {"required": False}],
    }

    CONSTANCE_CONFIG_FIELDSETS = {
        "EJ Options": (
            "EJ_MAX_BOARD_NUMBER",
            "EJ_LISTEN_TO_COMMUNITY_SIGNATURE_CONVERSATIONS_LIMIT",
            "EJ_LISTEN_TO_COMMUNITY_SIGNATURE_VOTE_LIMIT",
            "EJ_LISTEN_TO_CITY_SIGNATURE_CONVERSATIONS_LIMIT",
            "EJ_LISTEN_TO_CITY_SIGNATURE_VOTE_LIMIT",
            "EJ_LISTEN_TO_CITY_YEARLY_SIGNATURE_VOTE_LIMIT",
            "EJ_LISTEN_TO_CITY_YEARLY_SIGNATURE_CONVERSATIONS_LIMIT",
            "EJ_PROFILE_STATE_CHOICES",
            "EJ_LANDING_PAGE_DOMAIN",
            "RETURN_USER_SKIPED_COMMENTS",
        )
    }

    # Auxiliary options
    EJ_MAX_BOARD_NUMBER = os.getenv("{attr}", 1)

    EJ_LISTEN_TO_COMMUNITY_SIGNATURE_CONVERSATIONS_LIMIT = os.getenv("{attr}", 20)
    EJ_LISTEN_TO_COMMUNITY_SIGNATURE_VOTE_LIMIT = os.getenv("{attr}", 100000)

    EJ_LISTEN_TO_CITY_SIGNATURE_CONVERSATIONS_LIMIT = os.getenv("{attr}", 21)
    EJ_LISTEN_TO_CITY_SIGNATURE_VOTE_LIMIT = os.getenv("{attr}", 100000)

    EJ_LISTEN_TO_CITY_YEARLY_SIGNATURE_VOTE_LIMIT = os.getenv("{attr}", 1000000000)
    EJ_LISTEN_TO_CITY_YEARLY_SIGNATURE_CONVERSATIONS_LIMIT = os.getenv(
        "{attr}", 1000000000
    )

    RETURN_USER_SKIPED_COMMENTS = os.getenv("{attr}", True)

    EJ_PROFILE_STATE_CHOICES = (
        ("AC", "Acre"),
        ("AL", "Alagoas"),
        ("AP", "Amapá"),
        ("AM", "Amazonas"),
        ("BA", "Bahia"),
        ("CE", "Ceará"),
        ("DF", "Distrito Federal"),
        ("ES", "Espírito Santo"),
        ("GO", "Goiás"),
        ("MA", "Maranhão"),
        ("MT", "Mato Grosso"),
        ("MS", "Mato Grosso do Sul"),
        ("MG", "Minas Gerais"),
        ("PA", "Pará"),
        ("PB", "Paraíba"),
        ("PR", "Paraná"),
        ("PE", "Pernambuco"),
        ("PI", "Piauí"),
        ("RJ", "Rio de Janeiro"),
        ("RN", "Rio Grande do Norte"),
        ("RS", "Rio Grande do Sul"),
        ("RO", "Rondônia"),
        ("RR", "Roraima"),
        ("SC", "Santa Catarina"),
        ("SP", "São Paulo"),
        ("SE", "Sergipe"),
        ("TO", "Tocantins"),
    )

    EJ_LANDING_PAGE_DOMAIN = os.getenv("{attr}", "/login")

    CKEDITOR_CONFIGS = {
        "default": {
            "toolbar": "Custom",
            "toolbar_Custom": [
                [
                    "Font",
                    "Bold",
                    "Italic",
                    "Underline",
                    "Strike",
                    "TextColor",
                    "BGColor",
                    "SpecialChar",
                    "Undo",
                    "Redo",
                ],
                ["Link", "Unlink", "Smiley", "-"],
                [
                    "NumberedList",
                    "BulletedList",
                    "-",
                    "JustifyLeft",
                    "JustifyCenter",
                    "JustifyRight",
                ],
            ],
            "width": "auto",
            "allowedContent": False,
            "extraPlugins": ",".join(["placeholder"]),
            "editorplaceholder": "Insira sua mensagem aqui",
            "removePlugins": "exportpdf",
            "height": 140,
        },
    }
