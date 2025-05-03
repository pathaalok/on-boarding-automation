package com.example;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
@RefreshScope
@ConfigurationProperties(prefix = "rules")
public class RulesProperties {

    private Map<String, String> non_regulated_rccRule;
    private Map<String, String> inv_ref_id_rccRule;
    private Map<String, String> non_regulated_inv_ref_id_rccRule;

    public Map<String, String> getNon_regulated_rccRule() {
        return non_regulated_rccRule;
    }

    public void setNon_regulated_rccRule(Map<String, String> non_regulated_rccRule) {
        this.non_regulated_rccRule = non_regulated_rccRule;
    }

    public Map<String, String> getInv_ref_id_rccRule() {
        return inv_ref_id_rccRule;
    }

    public void setInv_ref_id_rccRule(Map<String, String> inv_ref_id_rccRule) {
        this.inv_ref_id_rccRule = inv_ref_id_rccRule;
    }

    public Map<String, String> getNon_regulated_inv_ref_id_rccRule() {
        return non_regulated_inv_ref_id_rccRule;
    }

    public void setNon_regulated_inv_ref_id_rccRule(Map<String, String> non_regulated_inv_ref_id_rccRule) {
        this.non_regulated_inv_ref_id_rccRule = non_regulated_inv_ref_id_rccRule;
    }
}
