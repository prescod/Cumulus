/*
    Copyright (c) 2018, Salesforce.org
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
* @date 2018
* @group Settings
* @group-content ../../ApexDocContent/Settings.htm
* @description Controller extension for the Data Import Fied Mapping settings panel.
*/
public with sharing class STG_PanelDataImportMapping_CTRL extends STG_Panel {

    /*********************************************************************************************************
    * @description Returns the string Id of the Data Import Mapping panel
    */
    public override string idPanel() { return 'idPanelDataImportMapping'; }

    /*******************************************************************************************************
    * @description is the panel currently Polling for deployment results
    */
    public Boolean isPolling {
        get {
            if (isPolling == null) {
                return false;
            } else {
                return isPolling;
            }
        }
        private set;
    }

    /*******************************************************************************************************
    * @description Maximum timeout for page polling, 12 = 1 minute
    */
    private static final Integer MAX_TIME_OUT = 12;

    /*******************************************************************************************************
    * @description ActionPoller count
    */
    private Integer timeoutCount = 0;

    /*******************************************************************************************************
    * @description Get custom data import settings
    */
    public Data_Import_Settings__c dataImportSettings = UTIL_CustomSettingsFacade.getDataImportSettings();

    /*******************************************************************************************************
    * @description Return boolean for the current field mapping method
    */
    public Boolean isDataImportFieldMapping {
        get {
            return dataImportSettings.Field_Mapping_Method__c == 'Data Import Field Mapping' ? true : false;
        }
        set;
    }

    /*******************************************************************************************************
    * @description is the running user an admin
    */
    public Boolean isAdmin {
        get {
            return STG_Panel.runningUserIsAdmin();
        }
        set;
    }

    /*******************************************************************************************************
    * @description the jobId of the deployment
    */
    public String jobId { get; private set; }
    public String deploymentId { get; private set; }

    /*******************************************************************************************************
    * @description List of help text mappings that conflicts with our packaged default custom metatadata type mappings
    */
    public List<BDI_HelpTextCMT.DataImportFieldMapping> conflictingCMTs {
        get {
            if (conflictingCMTs == null) {
                return new List<BDI_HelpTextCMT.DataImportFieldMapping>();
            } else {
                return conflictingCMTs;
            }
        }
        set;
    }

    /*******************************************************************************************************
    * @description List of custom metatadata type mappings pending deployment
    */
    public List<BDI_HelpTextCMT.DataImportFieldMapping> pendingCMTs {
        get {
            if (pendingCMTs == null) {
                return new List<BDI_HelpTextCMT.DataImportFieldMapping>();
            } else {
                return pendingCMTs;
            }
        }
        set;
    }

    //todo: try to reference conflicts, etc, directly in the utility instance variables
    @TestVisible
    private BDI_MigrationMappingUtility migrationMappingUtility;

    private String deploymentStatus;

    public STG_PanelDataImportMapping_CTRL() {
        this.migrationMappingUtility = new BDI_MigrationMappingUtility(new BDI_MigrationMappingHelper());
        //check custom settings to see if we have a previous deployment Id
        // If so, check its status
        // If completed, display error or success info, possibly allow re-attempt
        // If not yet completed, simply display status or something, but don't let them re-deploy until previous job is complete
        checkDeploymentStatus();
        // If status is pending or in progress, disable toggle
    }

    private Boolean hasDeploymentInProgress(){
        // check status of Id in custom settings - if in progress return true so we don't kick off another deploy while one is in progress
    }

    /*******************************************************************************************************
    * @description Action Method to enable CMDT mapping, save custom setting
    * @return null
    */
    public PageReference enableDataImportFieldMapping() {
        STG_SettingsManager_CTRL.idPanelCurrent = idPanel(); //Q: why do we do this here?

        //todo: implement hasDeploymentInProgress by getting Id from custom settings and running checkDeployStatus()
        if (hasDeploymentInProgress()) {
            //todo: display message that deployment is in progress.
            return;
        }

        Savepoint sp = Database.setSavepoint();
        try {
            isPolling = true;

            // Check to see if we have any existing help text mappings that conflict with our default cmt mappings
            migrationMappingUtility.buildCustomMetadataRecordsFromHelpText();

//            if (!migrationMappingUtility.conflictingCMTs.isEmpty()) {
            if (migrationMappingUtility.hasMappingConflict()) {
                isPolling = false;
                //todo: access instance variables directly
                conflictingCMTs = migrationMappingUtility.conflictingCMTs;
                pendingCMTs = migrationMappingUtility.pendingCMTs; //Q: why do we do this here?
                // TODO turn into custom label, placeholder warning message
                ApexPages.addMessage(new ApexPages.Message(ApexPages.Severity.WARNING, 'We\'ve found some conflicts. Please resolve them before proceeding.'));
            } else { //no conflicts, deploy!
//                jobId = migrationMappingUtility.convertLegacyHelpTextToCustomMetadata();
                deploymentId = migrationMappingUtility.deployCustomMetadata();
                isPolling = true;
            }

            //TODO: shouldn't need this if we mock
            if (Test.isRunningTest()) {
                jobId = '123';
            }
        } catch (Exception e) {
            Database.rollback(sp);
            ERR_Handler.processError(e, ERR_Handler_API.Context.STTG);
            ApexPages.addMessage(new ApexPages.Message(ApexPages.Severity.ERROR, e.getMessage()));
        }
        return null;
    }

    /*******************************************************************************************************
    * @description Action Method to disable CMDT mapping, save custom setting
    * @return void
    */
    //TODO: should we call this "disableAdvancedMapping()?"
    public PageReference disableDataImportFieldMapping() {
        STG_SettingsManager_CTRL.idPanelCurrent = idPanel();

        //TODO: all we need to do here is set the custom setting "isAdvancedMappingEnabled" to false and save it
        //todo:probably need to add isAdvancedMappingEnabled custom setting field

    }

    /*******************************************************************************************************
    * @description Action Method used by Poller to check status of CMDT deployment
    * @return void
    */
    public PageReference checkDeploymentStatus() {
        //TODO: use checkDeployStatus() https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_checkdeploystatus.htm

        //todo: get Id from settings (fresh ie always requery using checkDeployStatus())
        Id previousDeploymentRequestId = dataImportSettings.<deploymentIdField>;
        DeployResult deployResult = metadatabinding.checkDeployStatus(previousDeploymentRequestId, true);
        //inspect deploy result, set status, display to user or take action


        return null;
    }
}