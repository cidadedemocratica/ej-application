from ej_integrations.forms import OpinionComponentForm


class TestOpinionComponentForm:
    def test_xss_is_cleaned(self, db, conversation):
        form = OpinionComponentForm(
            {
                "conversation": conversation.id,
                "final_voting_message": (
                    "<div><script>alert(1)</script>"
                    '<a href="javascript:alert(1)" onclick="alert(2)">'
                    'safe</a><img src="x"></div>'
                ),
            }
        )

        assert form.is_valid()
        cleaned = form.cleaned_data["final_voting_message"]
        assert "script" not in cleaned
        assert "onclick" not in cleaned
        assert "javascript:" not in cleaned
        assert "<img" not in cleaned
        assert "safe" in cleaned

    def test_rich_text_formatting_is_preserved(self, db, conversation):
        rich_text = (
            "<p><strong>bold</strong> <u>underlined</u> <s>struck</s> "
            '<span style="font-family:Arial;color:red;background-color:blue;'
            'text-align:center;font-weight:bold">formatted</span></p>'
            "<ul><li>first</li></ul>"
            '<a href="https://example.com">link</a>'
        )
        form = OpinionComponentForm(
            {
                "conversation": conversation.id,
                "final_voting_message": rich_text,
            }
        )

        assert form.is_valid()
        cleaned = form.cleaned_data["final_voting_message"]
        assert "<strong>bold</strong>" in cleaned
        assert "<u>underlined</u>" in cleaned
        assert "<s>struck</s>" in cleaned
        assert "font-family:Arial" in cleaned
        assert "color:red" in cleaned
        assert "background-color:blue" in cleaned
        assert "text-align:center" in cleaned
        assert "font-weight:bold" in cleaned
        assert "<ul><li>first</li></ul>" in cleaned
        assert 'href="https://example.com"' in cleaned
