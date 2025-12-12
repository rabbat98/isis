import logging
from typing import Any

import ncs
from rfs.generic import GenericService
from sdn_nso_lib.ncs_utils.template import J2NSOTemplate

from .. import utils
from ..ressources import REFS_POLICY


class DeviceError(Exception):
    """Generic error communicating with device."""

class ServiceInputError(Exception):
    """Generic error due to service input."""

class IsisInterfaceService(GenericService):

    def __init__(
        self,
        service: ncs.maagic.ListElement,
        inventory_data: dict[str, Any],
    ) -> None:
        
        super().__init__(
            service=service,
            inventory_data=inventory_data,
            device_name_path="../device",
            template_ref=REFS_POLICY["leafref"][0],
        )
        self.root = ncs.maagic.get_root(service)

#################################################################
#   Definition des methode generiques au fournisseurs           #
#################################################################

    def add_all_vars(
        self,
        data_list: dict[str, Any],
        prefix: str,
        template_handler: J2NSOTemplate,
    ) -> None:

        merged_interface_type = self.data.get("interface_type", self.ncs_service.interface_type)
        merged_instance_id = self.data.get("isis_instance_id", self.ncs_service.isis_instance_id)

        isis_interface_common_vars = {
            "DEVICE": self.device.name,
            "INTERFACE_NAME": self.ncs_service.name,
            "INTERFACE_TYPE": merged_interface_type,
            "INSTANCE_ID": merged_instance_id,
        }

        logging.info(isis_interface_common_vars)
        template_handler.add_dict(isis_interface_common_vars)

        for var, val in data_list.items():
            if var == "passwd":
               continue 

        for var, val in data_list.items():

            if not isinstance(val, (dict, list, tuple, set)):
                if prefix == "":
                    new_prefix = var.upper()
                else:
                    new_prefix = f"{prefix}_{var.upper()}"

                if isinstance(val, bool):
                    vale = "true" if val else "false"
                else:
                    vale = val

                template_handler.add(new_prefix, vale, j2_data=self.j2_data)
                logging.info(f"{new_prefix} :  {vale}")

            if isinstance(val, dict):
                if prefix == "":
                    new_prefix = var.upper()
                else:
                    new_prefix = f"{prefix}_{var.upper()}"
                self.add_all_vars(val, new_prefix, template_handler)

#################################################################
#      specific methods                                         #
#################################################################

    def _prepare_common_data(self) -> dict[str, Any]:
        data: dict[str, Any] = dict(self.data)

        if "interface_type" not in data:
            it = getattr(self.ncs_service, "interface_type", None)
            if it not in (None, ""):
                data["interface_type"] = str(it)

        if "isis_instance_id" not in data:
            inst = getattr(self.ncs_service, "isis_instance_id", None)
            if inst not in (None, ""):
                data["isis_instance_id"] = str(inst)

        missing = []
        if not data.get("interface_type"):
            missing.append("interface-type")
        if not data.get("isis_instance_id"):
            missing.append("isis-instance-id")

        if missing:
            raise ServiceInputError("Missing mandatory leaves for ISIS interface "f"(must be set in service or inventory): {', '.join(missing)}")

        self.data = data
        return data

    def _template_suffix(self) -> str:
        interface_type = self.data.get("interface_type")
        if str(interface_type) == "loopback":
            return "loopback"
        return "common"

    def _get_loopback_attribs(self, data: dict[str, Any]) -> dict[str, Any]:
        loopback_data = (data.get("loopback_attribs")or data.get("loopback-attribs")or {})
        
        sr_id = (loopback_data.get("sr_id")or loopback_data.get("sr-id"))
        loopback_id = (loopback_data.get("loopback_id")or loopback_data.get("loopback-id"))
        unicast_tag = (loopback_data.get("unicast_tag")or loopback_data.get("unicast-tag"))

        if sr_id is None and unicast_tag is None and loopback_id is None:
            loopback = getattr(self.ncs_service, "loopback_attribs", None)
            if loopback is not None and loopback.exists():
                sr_id = getattr(loopback, "sr_id", None)
                loopback_id = getattr(loopback, "loopback_id", None)
                unicast_tag = getattr(loopback, "unicast_tag", None)

        return {
            "sr_id": sr_id,
            "loopback_id": loopback_id,
            "unicast_tag": unicast_tag
        }

    def _add_loopback_vars(self, tpl: J2NSOTemplate, data: dict[str, Any]) -> None:
        tpl.add("NAME", self.ncs_service.name, j2_data=self.j2_data)
        attribs = self._get_loopback_attribs(data)

        tpl.add("LOOPBACK_SR_ID",str(attribs["sr_id"]) if attribs["sr_id"] is not None else "None",j2_data=self.j2_data)
        tpl.add("LOOPBACK_UNICAST_TAG",str(attribs["unicast_tag"]) if attribs["unicast_tag"] is not None else "None",j2_data=self.j2_data)


#################################################################
#   Methodes specifiques ALUSR                                  #
#################################################################

    def apply_nokia(self) -> None:
        data = self._prepare_common_data()

        tpl = J2NSOTemplate(self.ncs_service, j2_filters=self.j2_filters)
        self.add_all_vars(data, "", tpl)

        passwd = data.get("passwd") or getattr(self.ncs_service, "passwd", None)
        if passwd:
            tpl.add("PASSWD", passwd, j2_data=self.j2_data)
        else:
            tpl.add("PASSWD", "None", j2_data=self.j2_data)

        suffix = self._template_suffix()

        if suffix == "loopback":
            self._add_loopback_vars(tpl, data)
  
        tpl.apply(f"alu-sr-cli/alu-sr-cli-isis-interface-{suffix}-template")

##################################################################
#   Methodes specifiques IOSXR                                  #
##################################################################

    def apply_iosxr(self) -> None:
        data = self._prepare_common_data()
        logging.info("SELF.DATA -> %r" , data)

        tpl = J2NSOTemplate(self.ncs_service, j2_filters=self.j2_filters)
        self.add_all_vars(data, "", tpl)

        passwd = data.get("passwd") or getattr(self.ncs_service, "passwd", None)
        if passwd:
            encrypted = utils.generate_isis_passwd(self.root,passwd,self.device.name,self.ncs_service.name)
            tpl.add("PASSWD", encrypted, j2_data=self.j2_data)
        else:
            tpl.add("PASSWD", "None", j2_data=self.j2_data)   

        suffix = self._template_suffix()
        if suffix == "loopback":
            self._add_loopback_vars(tpl, data)

        tpl.add("ENABLE_SYNC_LDP", "True" if data.get("enable_sync_ldp") else "False", j2_data=self.j2_data)

        tpl.apply(f"cisco-iosxr-cli/cisco-iosxr-cli-isis-interface-{suffix}-template")

#################################################################
#   Methodes specifiques huawei-vrp                             #
#################################################################

    def apply_huawei(self) -> None:
        data = self._prepare_common_data()

        circuit_type = data.get("circuit_type")
        if circuit_type == "level-2-only":
            data["circuit_type"] = "level-2"

        tpl = J2NSOTemplate(self.ncs_service, j2_filters=self.j2_filters)
        self.add_all_vars(data, "", tpl)

        suffix = self._template_suffix()

        if suffix == "common":
            common_data = (data.get("common_attributes") or data.get("common-attributes")  or {} )

            interface_id = common_data.get("id")
            interface_subif_id = ( common_data.get("subif_id") or common_data.get("subif-id") )
            if_attr_type = common_data.get("type")

            common_attr = getattr(self.ncs_service, "common_attributes", None)
            if (interface_id is None or if_attr_type is None) and common_attr is not None and common_attr.exists():
                if_attr_type = if_attr_type or common_attr.type
                interface_id = interface_id or common_attr.id
                if interface_subif_id is None:
                    interface_subif_id = common_attr.subif_id

            if interface_id is None or if_attr_type is None:
                raise ServiceInputError( "Please provide common-attributes to the service (id, type or subif-id)")

            if if_attr_type != "LAG":
                raise ServiceInputError("Template must be updated to manage ISIS on physical interfaces")

            interface_name = ( f"{interface_id}.{interface_subif_id}" if interface_subif_id is not None else interface_id )

            tpl.add("IF_ATTR_TYPE", if_attr_type, j2_data=self.j2_data)
            tpl.add("NAME", interface_name, j2_data=self.j2_data)

            tpl.apply("huawei-vrp-cli/huawei-vrp-cli-isis-interface-common-template")
            return

        elif suffix == "loopback":
            attribs = self._get_loopback_attribs(data)
            
            loopback_id = attribs["loopback_id"]
            unicast_tag = attribs["unicast_tag"]

            if loopback_id is None:
                raise ServiceInputError("Please provide loopback-id in loopback-attribs for Huawei loopback interface")

            tpl.add("LOOPBACK_ID", str(loopback_id), j2_data=self.j2_data)
            tpl.add("LOOPBACK_UNICAST_TAG",str(unicast_tag) if unicast_tag is not None else "None", j2_data=self.j2_data)

            tpl.apply("huawei-vrp-cli/huawei-vrp-cli-isis-interface-loopback-template")
            return

        tpl.apply(f"huawei-vrp-cli/huawei-vrp-cli-isis-interface-{suffix}-template")

#################################################################
# Methodes apply                                                #
#################################################################

    def apply(self) -> None:
        ned = self.device.ned_type
        logging.info(ned)
        if ned == "cisco-iosxr-cli":
            self.apply_iosxr()
        elif ned == "alu-sr-cli":
            self.apply_nokia()
        elif ned == "huawei-vrp-cli":
            self.apply_huawei()
        else:
            raise NotImplementedError(f"NED {ned} not supported for ISIS interface")