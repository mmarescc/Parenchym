import deform.form
from pym.i18n import tsf as _


def submit_button():
    return deform.form.Button(name='submit', type='submit', value=_("Submit"))