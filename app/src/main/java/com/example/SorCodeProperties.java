package com.example;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@RefreshScope
@ConfigurationProperties(prefix = "sor-codes")
public class SorCodeProperties {

    private List<String> Acct;
    private List<String> DEAL;

    public List<String> getAcct() {
        return Acct;
    }

    public void setAcct(List<String> acct) {
        Acct = acct;
    }

    public List<String> getDEAL() {
        return DEAL;
    }

    public void setDEAL(List<String> DEAL) {
        this.DEAL = DEAL;
    }
}
