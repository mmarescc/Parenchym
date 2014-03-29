import deform.form
import pyramid.i18n
import pym.i18n

_ = pyramid.i18n.TranslationStringFactory(pym.i18n.DOMAIN)


def submit_button():
    return deform.form.Button(name='submit', type='submit', value=_("Submit"))