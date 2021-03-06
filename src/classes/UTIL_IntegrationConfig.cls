/*
    Copyright (c) 2019, Salesforce.org
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Salesforce.org nor the names of
      its contributors may be used to endorse or promote products derived
      from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
    FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
    COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
    INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
    BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
    CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
    LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
    ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.
*/
/**
* @author Salesforce.org
* @date 2019
* @group API
* @description Config for external packages
*/
public abstract with sharing class UTIL_IntegrationConfig {
    public Enum Integration {
        ArchiveBridge
    }

    @TestVisible
    private static final String DEFAULT_ARCHIVE_BRIDGE_NAMESPACE = 'dso_npsp';

    @TestVisible
    protected Boolean isInstalled {
        get {
            if (isInstalled == null) {
                isInstalled = initIsInstalled();
            }
            return isInstalled;
        }
        set;
    }
    @TestVisible
    protected String namespace {
        get {
            if (namespace == null) {
                namespace = initNamespace();
            }
            return namespace;
        }
        set;
    }

    @TestVisible
    protected String callableApiClassName;

    @TestVisible
    protected System.Callable callableApi {
        get {
            if (callableApi == null) {
                callableApi = initCallableApi();
            }
            return callableApi;
        }
        set;
    }

    /**********************************************************************************************************
    * @description Checks if the package is installed
    */
    protected abstract Boolean initIsInstalled();

    /**********************************************************************************************************
    * @description Determines the package namespace
    */
    protected abstract String initNamespace();

    /**********************************************************************************************************
    * @description Confirms if the (un)managed package is installed
    */
    public Boolean isInstalled() {
        return isInstalled;
    }

    /**********************************************************************************************************
    * @description Instantiate the Callable API endpoint in the package
    */
    public System.Callable getCallableApi() {
        return callableApi;
    }

    /**********************************************************************************************************
    * @description Instantiate the Callable API endpoint in the package
    */
    private System.Callable initCallableApi() {
        if (!isInstalled) {
            return null;
        }

        return (Callable) Type.forName(namespace, callableApiClassName).newInstance();
    }

    /**********************************************************************************************************
    * @description Adds the namespace before an SObject name or a child relationship name
    */
    public String prefixNamespace(String entity) {
        if (String.isBlank(namespace)) {
            return entity;
        }

        return namespace + '__' + entity;
    }

    /**********************************************************************************************************
    * @description Builds an instance of UTIL_IntegrationConfig based on the passed in Enum
    * @param Integration enum for desired packag
    * @returns UTIL_IntegrationConfig
    */
    public static UTIL_IntegrationConfig getConfig(Integration integrationPackage) {
        switch on integrationPackage {

            when ArchiveBridge {
                return new ArchiveBridgeConfig();
            }

            when else {
                return null;
            }
        }
    }

    public class ArchiveBridgeConfig extends UTIL_IntegrationConfig {
        /**********************************************************************************************************
        * @description Constructor
        */
        public ArchiveBridgeConfig() {
            callableApiClassName = 'BridgeCallableAPI';
        }

        /**********************************************************************************************************
        * @description Checks if the package is installed
        */
        protected override Boolean initIsInstalled() {
            Schema.SObjectType archiveRollupSummaryType =
                Schema.getGlobalDescribe().get(prefixNamespace('ArchiveRollupSummary__b'));

            if (archiveRollupSummaryType == null) {
                return false;
            }

            Schema.SObjectField rollupTypeField = archiveRollupSummaryType
                .getDescribe()
                .fields 
                .getMap()
                .get(prefixNamespace('RollupType__c'));

            return rollupTypeField != null;
        }

        /**********************************************************************************************************
        * @description Determines the package namespace
        */
        protected override String initNamespace() {
            final String NAMESPACED_ARCHIVE_SUMMARY = DEFAULT_ARCHIVE_BRIDGE_NAMESPACE + '__ArchiveRollupSummary__b';

            if (System.Type.forName(NAMESPACED_ARCHIVE_SUMMARY) != null) {
                return DEFAULT_ARCHIVE_BRIDGE_NAMESPACE;
            } else {
                return '';
            }
        }
    }
}