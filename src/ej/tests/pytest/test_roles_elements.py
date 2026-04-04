import pytest

from ej.roles import intro
from ej.roles.tags import icon


class TestRolesElements:
    """
    Test CSS roles elements.
    """

    def test_create_paragraph_with_title_and_description(self):
        title_test = "Test"
        desc_test = "Something about test..."
        p = intro(title_test, description=desc_test)
        assert p.tag == "div"
        if len(p.children) == 2:
            ph1 = p.children[0]
            pp = p.children[1]
            # tags from every element created using paragraph
            assert ph1.tag == "h1" and pp.tag == "p"
            if len(ph1.children) == 1:
                title = ph1.children[0]
                assert title.json()["text"] == title_test
            else:
                pytest.fail("Paragraph from roles hasn't text inside of h1.")

            if len(pp.children) == 1:
                desc = pp.children[0]
                assert desc.json()["text"] == desc_test
            else:
                pytest.fail(
                    "Paragraph from roles hasn't text description inside of p."
                )
        else:
            pytest.fail(
                "Paragraph from roles hasn't h1 title or description p."
            )

    def test_create_icon_with_name_and_href(self):
        icon_name_test = "Icon test"
        href_test = "/tmp/icon.png"
        i = icon(icon_name_test, href=href_test)
        assert i.tag == "a" and i.attrs["href"] == href_test
        if len(i.children) == 1:
            ii = i.children[0]
            iclass = ii.attrs["class"]
            assert ii.tag == "i" and any(
                icon_name_test in tag for tag in iclass
            )
        else:
            pytest.fail("Icon from roles hasn't i.")
