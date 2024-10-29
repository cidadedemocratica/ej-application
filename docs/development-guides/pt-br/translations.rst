.. _Translations:

=========================
Internalização e tradução
=========================

Para identificar qual tradução utilizar, são utilizadas variáveis de ambiente. É importante ressaltar
que os textos escritos em código, sejam em templates ou em help_text de forms, ou em outro lugar de códigos
são todos escritos em *inglês* para que depois possão ser traduzidos para *português*. Essas
são os dois idiomas disponíveis na EJ atualmente.

COUNTRY (Brazil):
    O País é utilizado para localização e internacionalização da plataforma. Esta configuração
    controla simultaneamente as variáveis DJANGO_LOCALE_NAME, DJANGO_LANGUAGE_CODE
    e DJANGO_TIME_ZONE usando as configurações padrão para o seu
    país. Os países são especificados pelo nome (por exemplo, USA, Brazil, Argentina,
    Canadá, etc). Você pode usar um PAÍS como base e personalizar qualquer variável
    de forma independente (por exemplo, COUNTRY = "Canadá", LANGUAGE_CODE = "fr-ca")

Na pasta /locale/ estão os arquivos relacionados a traduções:

* É no arquivo django.po que deve-se atualizar as traduções
* Os arquivos django.mo e django.po~ não devem ser alterados;

Dentro do arquivo *django.po* são exibidos todos os trechos de texto que podem ser traduzidos, como no exemplo:

.. code-block:: python

    #: src/ej_integrations/jinja2/ej_integrations/ndex.jinja2:20
    #, fuzzy
    msgid "Integration"
    msgstr "Integração"


Nesse texto, observa-se no código o texto "Integration" na linha 20 do index.jinja, arquivo encontrado no caminho
que está descrito, e a tradução que foi escrita é a "Integração", é essa que podemos alterar e acrescentar no texto.

Ao adicionar um texto novo e querer que haja sua tradução, é necessário que executemos:

.. code-block:: shell

    $ inv i18n

Assim, aparecerá no arquivo django.po o texto para que seja colocado a *msgstr* em português.
Para certificar-se que a tradução será corretamente exibida, você deve executar:

.. code-block:: shell

    $ inv i18n --compile

Mas como o código sabe o que deve traduzir? Quando uma string em python deve ser traduzida devemos realizar o seguinte:


.. code-block:: python

    from django.utils.translation import gettext_lazy as _


    variable = _("This string should be translated")


Já nos arquivos jinja2 existem duas formas, sendo a segunda recomendada para techos maiores:

.. code-block:: jinja

    {{ _('This string should be translated') }}

    or

    {% trans %}
        This string should be translated
    {% endtrans %}
