from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2024, Jim Miller'
__docformat__ = 'restructuredtext en'

## References:
## https://www.mobileread.com/forums/showthread.php?p=4435205&postcount=65
## https://www.mobileread.com/forums/showthread.php?p=4102834&postcount=389

from calibre_plugins.action_chains.events import ChainEvent

class FanFicFareDownloadFinished(ChainEvent):

    # replace with the name of your event
    name = 'FanFicFare Download Finished'

    def get_event_signal(self):
        return self.gui.iactions['FanFicFare'].download_finished_signal
