# -*- mode: python; python-indent: 4 -*-

import ncs
from typing import Any
from ncs.application import Service
from inventory_manager.api import InventoryManager
from .ressources import REFS_POLICY

from .logic_handlers.isis_instance import IsisInstanceService 
from .logic_handlers.isis_interface import IsisInterfaceService 

class DeviceError(Exception):
    """Generic error communicating with device."""

class ServiceInputError(Exception):
    """Generic error due to service input"""

class IsisInstance(Service):
    
    @Service.create  # type: ignore
    @InventoryManager.subscribe(REFS_POLICY)  
    def cb_create(
        self,
        tctx: Any,
        root: ncs.maagic.Root,
        service: ncs.maagic.ListElement,
        proplist: tuple[str, str],
        inventory: dict[str, Any],
    ) -> None:

        specific_logics: dict[str, type[IsisInstanceService]] = {}
        service_class: type[IsisInstanceService]
        if service.inventory_logic.name in specific_logics:
            service_class = specific_logics[service.inventory_logic.name]
        else:
            service_class = IsisInstanceService
        rfs_service = service_class(
            service=service, inventory_data=inventory
        )
        rfs_service.apply()



class IsisInterface(Service):
    
    @Service.create  # type: ignore
    @InventoryManager.subscribe(REFS_POLICY)  
    def cb_create(
        self,
        tctx: Any,
        root: ncs.maagic.Root,
        service: ncs.maagic.ListElement,
        proplist: tuple[str, str],
        inventory: dict[str, Any],
    ) -> None:

        specific_logics: dict[str, type[IsisInterfaceService]] = {}
        service_class: type[IsisInterfaceService]
        if service.inventory_logic.name in specific_logics:
            service_class = specific_logics[service.inventory_logic.name]
        else:
            service_class = IsisInterfaceService
        rfs_service = service_class(
            service=service, inventory_data=inventory
        )
        rfs_service.apply()


class IsisInventory(Service):
    @Service.create  # type: ignore
    @InventoryManager.publish
    def cb_create(
        self,
        tctx: Any,
        root: ncs.maagic.Root,
        service: ncs.maagic.ListElement,
        proplist: tuple[str, str]
    ) -> None:
        return 


# --------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# --------------------------------------------

class Main(ncs.application.Application):
    """NCS class to register action & service callbacks"""
    
    def setup(self) -> None:
        self.log.info("Main RUNNING")
        
        self.register_service("isis-instance-servicepoint", IsisInstance, "isis-instance")
        self.register_service("isis-interface-servicepoint", IsisInterface, "isis-interface")
        
        self.register_service("isis-inventory-servicepoint", IsisInventory, "isis-inventory")

    def teardown(self) -> None:
        self.log.info("Main FINISHED")
