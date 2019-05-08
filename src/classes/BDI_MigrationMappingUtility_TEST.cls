/**
 * Created by kenneth.lewis on 2019-05-08.
 */

@IsTest
private class BDI_MigrationMappingUtility_TEST {

    @IsTest
    static void migrationUtilityCreatesCustomMetadataRecordsFromHelpText() {
        //1. Set the mock
        // Create a mock version of the BDI_MigrationUtilityHelper class.
        BDI_MigrationMappingHelper mockMigrationMappingHelper =
                (BDI_MigrationMappingHelper) Test.createStub(
                        BDI_MigrationMappingHelper.class,
                        new BDI_MigrationMappingHelperMock());

        //2. Call the method
        BDI_MigrationMappingUtility util = new BDI_MigrationMappingUtility();
        util.buildCustomMetadataRecordsFromHelpText();

        //3. Verify results
        List<Data_Import_Field_Mapping__mdt> dataImportFieldMappings = getDataImportFieldMappings();
        System.debug(LoggingLevel.ERROR, '*** variable value: ' + dataImportFieldMappings);
        System.assertEquals(1, dataImportFieldMappings.size());
    }

    private static List<Data_Import_Field_Mapping__mdt> getDataImportFieldMappings(){
        return [SELECT Id, Label, DeveloperName, Source_Field_API_Name__c FROM Data_Import_Field_Mapping__mdt];
    }
}