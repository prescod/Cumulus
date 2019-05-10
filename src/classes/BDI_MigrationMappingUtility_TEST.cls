/**
 * Created by kenneth.lewis on 2019-05-08.
 */

@IsTest
private class BDI_MigrationMappingUtility_TEST {

    @IsTest
    static void migrationUtilityCreatesCustomMetadataRecordsFromHelpText() {
        //1. Set the mock
        // Create a mock version of the BDI_MigrationUtilityHelper class.
        BDI_MigrationMappingHelper mock_BDI_MigrationMappingHelper =
                (BDI_MigrationMappingHelper) Test.createStub(
                        BDI_MigrationMappingHelper.class,
                        new BDI_MigrationMappingHelperMock());

        //2. Call the method
        BDI_MigrationMappingUtility util = new BDI_MigrationMappingUtility();
        util.buildCustomMetadataRecordsFromHelpText(mock_BDI_MigrationMappingHelper);

        //3. Verify results - if we were doing regular DML for the net new (pending) mappings, we might do this to verify:
        List<Data_Import_Field_Mapping__mdt> mockedDataImportFieldMappings = getMockedDataImportFieldMappings();
//        System.assertEquals(2, mockedDataImportFieldMappings.size());

        //But since we are deploying the metadata, we'll probably need to simply inspect the property of the instance
        System.debug(LoggingLevel.ERROR, '*** variable value: ' + util.pendingCMTs);
        //Confirm that "pendingCMTs" now contains the mocked mappings that will be deployed...
        //...
        //...
    }

    private static List<Data_Import_Field_Mapping__mdt> getMockedDataImportFieldMappings() {
        return [
                SELECT Id, Label, DeveloperName, Source_Field_API_Name__c
                FROM Data_Import_Field_Mapping__mdt
                WHERE Label IN ('1','2')
        ];
    }
}