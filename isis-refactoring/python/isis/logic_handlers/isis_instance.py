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
    
class IsisInstanceService(GenericService):

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

#################################################################
#   Definition des methode generiques au fournisseurs           #
#################################################################

    def add_all_vars(
        self,
        data_list: dict[str, Any],
        prefix: str,
        template_handler: J2NSOTemplate,
    ) -> None:

        isis_common_vars = {
            "DEVICE": self.device.name,
            "INSTANCE_ID": self.ncs_service.instance_id,
        }
        logging.info(isis_common_vars)
        template_handler.add_dict(isis_common_vars)

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
                logging.info(f'{new_prefix} :  {vale}')
       

            if isinstance(val, dict):
                if prefix == "":
                    new_prefix = var.upper()
                else:
                    new_prefix = f"{prefix}_{var.upper()}"
                self.add_all_vars(val, new_prefix, template_handler)

#################################################################
#      specific methods                                         #
#################################################################

    mandatory_leaves = {
        "cisco": ["area_id", "loopback0"],
        "nokia": ["area_id", "loopback0"],
        "huawei": ["area_id", "loopback0"],
    }

    def _prepare_common_data(self) -> dict[str, Any]:

        data: dict[str, Any] = dict(self.data)

        if "net_id" not in data:
            loopback = data.get("loopback0")
            area_id = data.get("area_id")
            if loopback and area_id:
                data["net_id"] = utils.generate_net_id(loopback, area_id)
        return data
    
  
    def _add_sr_vars(self, data, tpl):
       sr = data.get("sr") or {}
       tpl.add("SR", "True" if sr else "False", j2_data=self.j2_data)
       tpl.add("SR_LOWER_BOUND", sr.get("lower_bound") or "", j2_data=self.j2_data)
       tpl.add("SR_UPPER_BOUND", sr.get("upper_bound") or "", j2_data=self.j2_data)

#################################################################
#   Methodes specifiques ALUSR                                  #
#################################################################

    def apply_nokia(self) -> None:
        ned = "nokia"
        for leaf in self.mandatory_leaves[ned]:
            value = self.data.get(leaf)
            if value is None:
                raise ServiceInputError(f"{leaf} must be configured for ISIS instance "f"{self.ncs_service.instance_id}")
        self.apply_alusr_isis_instance()

    def apply_alusr_isis_instance(self) -> None:
        data = self._prepare_common_data()
        tpl = J2NSOTemplate(self.ncs_service, j2_filters=self.j2_filters)

        self.add_all_vars(data, "", tpl)

        self._add_sr_vars(data, tpl)

        tpl.add("DISABLE_SYNC_LDP", "True" if data.get("disable_sync_ldp") else "False", j2_data=self.j2_data)
        tpl.add("EXPORT", data.get("export") or "None", j2_data=self.j2_data)
        tpl.add("EXPORT_TUNNEL_TABLE", data.get("export_tunnel_table") or "None", j2_data=self.j2_data)

        tpl.apply("alu-sr-cli/alu-sr-cli-isis-instance-template")


#################################################################
#   Methodes specifiques IOSXR                                  #
#################################################################

    def apply_cisco(self) -> None:
        ned = "cisco"
        for leaf in self.mandatory_leaves[ned]:
            value = self.data.get(leaf)
            if value is None:
                raise ServiceInputError(f"{leaf} must be configured for ISIS instance "f"{self.ncs_service.instance_id}")
        self.apply_iosxr_isis_instance()

    def apply_iosxr_isis_instance(self) -> None:
        data = self._prepare_common_data()

        logging.info("SELF.DATA -> %r" , data)

        tpl = J2NSOTemplate(self.ncs_service, j2_filters=self.j2_filters)
        self.add_all_vars(data, "", tpl)

        self._add_sr_vars(data, tpl)

        ldp_enabled = isinstance(data.get("ldp"), dict) or data.get("ldp") is True
        tpl.add("LDP", "True" if ldp_enabled else "False", j2_data=self.j2_data)

        tpl.add("MPLS", "True" if data.get("mpls") else "False", j2_data=self.j2_data)
        tpl.add("MPLS_SR_PREFER", "True" if data.get("mpls_sr_prefer") else "False", j2_data=self.j2_data)
        tpl.add("DIST_LINK_STATE", "True" if data.get("dist_link_state") else "False", j2_data=self.j2_data)

        tpl.apply("cisco-iosxr-cli/cisco-iosxr-cli-isis-instance-template")

#################################################################
#   Methodes specifiques huawei-vrp                             #
#################################################################

    def apply_huawei(self) -> None:
        
        ned = "huawei"
        for leaf in self.mandatory_leaves[ned]:
            value = self.data.get(leaf)
            if value is None:
                raise ServiceInputError(f"{leaf} must be configured for ISIS instance "f"{self.ncs_service.instance_id}")
        self.apply_huawei_isis_instance()

    def apply_huawei_isis_instance(self) -> None:
        data = self._prepare_common_data()

        if "is_name" not in data:
            data["is_name"] = self.device.name

        tpl = J2NSOTemplate(self.ncs_service, j2_filters=self.j2_filters) 
        self.add_all_vars(data, "", tpl)
                
        self._add_sr_vars(data, tpl)
        
        fr = data.get("fast_reroute") or {}
        ti_lfa_level = fr.get("ti_lfa_level") or ""
        tpl.add( "FAST_REROUTE_TI_LFA_LEVEL", ti_lfa_level, j2_data=self.j2_data)

        tpl.apply("huawei-vrp-cli/huawei-vrp-cli-isis-instance-template")
        
#################################################################
# Methodes apply                                                #
#################################################################

    def apply(self) -> None:

        ned = self.device.ned_type
        logging.info(ned)
        if ned == "cisco-iosxr-cli":
            self.apply_cisco()
        elif ned == "alu-sr-cli":
            self.apply_nokia()
        elif ned == "huawei-vrp-cli":
            self.apply_huawei()
        else:
            raise NotImplementedError(f"NED {ned} not supported for ISIS instance")
