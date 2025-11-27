import asyncio
from PySide6.QtCore import QThread, Signal
from media_providers.radio.radio_service import RadioService


class RadioWorker(QThread):
    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self, service: RadioService, operation: str, params: dict):
        super().__init__()
        self.service = service
        self.operation = operation
        self.params = params
    
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if self.operation == 'countries':
                result = loop.run_until_complete(
                    self.service.get_countries(**self.params)
                )
            elif self.operation == 'languages':
                result = loop.run_until_complete(
                    self.service.get_languages(**self.params)
                )
            elif self.operation == 'tags':
                result = loop.run_until_complete(
                    self.service.get_tags(**self.params)
                )
            elif self.operation == 'search':
                result = loop.run_until_complete(
                    self.service.search_stations(**self.params)
                )
            elif self.operation == 'filter':
                result = loop.run_until_complete(
                    self.service.get_stations_by_filter(**self.params)
                )
            elif self.operation == 'favorites':
                result = self.service.get_favorites()
            elif self.operation == 'click':
                loop.run_until_complete(
                    self.service.click_station(self.params['uuid'])
                )
                result = None
            else:
                result = None
            
            loop.close()
            self.finished.emit(result)
                
        except Exception as e:
            self.error.emit(str(e))
