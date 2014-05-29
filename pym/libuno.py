#############################################################################
# Code inspired by
#
# - unoconv by Dag Wieers <dag@wieers.com>
# - OOoLib by Danny Brewer <d29583@groovegarden.com>
#   http://www.oooforum.org/forum/viewtopic.phtml?p=56037#56037
#   see also Danny's Python libs: http://www.oooforum.org/forum/viewtopic.phtml?t=14409
#
#############################################################################

import logging
import subprocess
import os
import sys
# We need system's dist-packages to have uno inside a virtualenv
import time

sys.path.append('/usr/lib/python3/dist-packages')
# noinspection PyUnresolvedReferences
import uno

# noinspection PyUnresolvedReferences
from com.sun.star.beans import PropertyValue
# noinspection PyUnresolvedReferences
from com.sun.star.connection import NoConnectException
# noinspection PyUnresolvedReferences
from com.sun.star.document.UpdateDocMode import QUIET_UPDATE
# noinspection PyUnresolvedReferences
from com.sun.star.lang import DisposedException, IllegalArgumentException
# noinspection PyUnresolvedReferences
from com.sun.star.io import IOException, XOutputStream
# noinspection PyUnresolvedReferences
from com.sun.star.script import CannotConvertException
# noinspection PyUnresolvedReferences
from com.sun.star.uno import Exception as UnoException
# noinspection PyUnresolvedReferences
from com.sun.star.uno import RuntimeException

import pym.lib


# noinspection PyPep8Naming
def uno_props(**args):
    props = []
    for key in args:
        prop = PropertyValue()
        prop.Name = key
        prop.Value = args[key]
        props.append(prop)
    return tuple(props)


# noinspection PyPep8Naming
class Listener():
    __metaclass__ = pym.lib.SingletonType

    def __init__(self, office='soffice', host='127.0.0.1', port=2002, pipe='dmoffice', lgg=None):
        """
        Connects to an office listener.

        Spawns a new headless office process if listener is not present,
        else connects to present one.

        Connection is made either via Unix domain socket (pipe) or via TCP/IP.
        If param:`pipe` is present, it takes precedence over host/port.

        Pipe is by far faster than network.

        :param office: Name of office executable, can have full path.
        :param host: IP address of listener
        :param port: Port number of listener
        :param pipe: Name of a Unix socket
        :param lgg: Instance of a logger (optional)
        """
        self.office = office
        self.host = host
        self.port = port
        self.pipe = pipe
        if not lgg:
            lgg = logging.getLogger(__name__)
        self.lgg = lgg
        if pipe:
            self.conn = "pipe,name={};urp;StarOffice.ComponentContext".format(pipe)
        else:
            self.conn = "socket,host={},port={};urp;StarOffice.ComponentContext".format(host, port)
        self.product = None
        self.context = None
        self.svcmgr = None
        self.proc = None
        self._desktop = None
        self._core_reflection = None
        self.connect()

    def __del__(self):
        self.close()

    def close(self):
        if self.proc:
            self.proc.terminate()

    def load_doc(self, url):
        if not '://' in url:
            url = 'file://' + os.path.abspath(os.path.normpath(url))
        return self.desktop.loadComponentFromURL(
            url,
            "_blank",
            0,
            ()
        )

    def new_doc(self, which):
        """
        Creates a new document.

        :param which: 'scalc', 'swriter', etc
        """
        return self.desktop.loadComponentFromURL(
            "private:factory/{}".format(which),
            "_blank",
            0,
            ()
        )

    @property
    def desktop(self):
        if not self._desktop:
            self._desktop = self.create_service('com.sun.star.frame.Desktop')
        return self._desktop

    @property
    def core_reflection(self):
        if not self._core_reflection:
            self._core_reflection = self.create_service(
                'com.sun.star.reflection.CoreReflection'
            )
        return self._core_reflection

    def create_struct(self, cTypeName):
        oXIdlClass = self.core_reflection.forName(cTypeName)
        # Create the struct.
        oReturnValue, oStruct = oXIdlClass.createObject(None)
        return oStruct

    def create_service(self, cClass):
        oObj = self.svcmgr.createInstance(cClass)
        return oObj

    def connect(self):

        def start_process():
            try:
                self.proc = subprocess.Popen(
                    [
                        self.office,
                        "--headless",
                        "--invisible",
                        "--nocrashreport",
                        "--nodefault",
                        "--nologo",
                        "--nofirststartwizard",
                        "--norestore",
                        "--accept={}".format(self.conn)
                    ],
                    env=os.environ
                )
            except subprocess.CalledProcessError as exc:
                self.lgg.exception(exc)
                self.lgg.error("Failed to start {} with '{}'".format(
                    self.office, self.conn
                ))
            else:
                # Give it time to initialise the socket
                time.sleep(1)
                self.lgg.debug("Created listener {} with '{}'".format(
                    self.office, self.conn
                ))

        # Init local objects
        context = uno.getComponentContext()
        svcmgr = context.ServiceManager
        resolver = svcmgr.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver",
            context
        )
        self.product = svcmgr.createInstance(
            "com.sun.star.configuration.ConfigurationProvider"
        ).createInstanceWithArguments(
            "com.sun.star.configuration.ConfigurationAccess",
            uno_props(nodepath="/org.openoffice.Setup/Product")
        )
        # Try to connect to existing process
        # If that fails, start office process and connect again
        try:
            context = resolver.resolve("uno:{}".format(self.conn))
        except NoConnectException as e:
            start_process()
            context = resolver.resolve("uno:{}".format(self.conn))
        else:
            self.lgg.debug('Connected to existing listener {}'.format(
                self.product.ooName
            ))
        # Now init ourselves with remote objects
        self.context = context
        self.svcmgr = self.context.ServiceManager

    def version(self):
        return (
            'Platform {}/{}'.format(os.name, sys.platform),
            'Python {}'.format(sys.version.replace("\n", '')),
            '{} {}'.format(self.product.ooName, self.product.ooSetupVersion)
        )

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    l = Listener()
    doc = l.new_doc('scalc')