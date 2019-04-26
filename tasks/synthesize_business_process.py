import os
import re
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce import BaseSalesforceApiTask, Deploy
from cumulusci.utils import temporary_dir

SOBJECT_METADATA = """<?xml version="1.0" encoding="utf-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <businessProcesses>
        <fullName>{business_process_name}</fullName>
        <isActive>true</isActive>
        <values>
            <fullName>{stage_name}</fullName>
            <default>false</default>
        </values>
    </businessProcesses>
    <recordTypes>
        <fullName>{record_type_developer_name}</fullName>
        <active>true</active>
        <businessProcess>{business_process_name}</businessProcess>
        <label>{record_type_label}</label>
    </recordTypes>
</CustomObject>
"""

PACKAGE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>*</members>
        <name>CustomObject</name>
    </types>
    <version>45.0</version>
</Package>"""


class SynthesizeBusinessProcess(BaseSalesforceApiTask):
    task_options = {
        "business_process_name": {
            "description": "The name of the Business Process.",
            "required": True,
        },
        "record_type_developer_name": {
            "description": "The Developer Name of the Record Type (unique).  Must contain only alphanumeric characters and underscores.",
            "required": True,
        },
        "record_type_label": {
            "description": "The Label of the Record Type.",
            "required": True,
        },
        "sobject": {
            "description": "The sObject on which to deploy the Record Type and Business Process.",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super(SynthesizeBusinessProcess, self)._init_options(kwargs)

        # Validate developer name
        if not re.match(r"^\w+$", self.options["record_type_developer_name"]):
            raise TaskOptionsError(
                "Record Type Developer Name value must contain only alphanumeric or underscore characters"
            )

    def _build_package(self):
        objects_app_path = "objects"
        os.mkdir(objects_app_path)
        with open(
            os.path.join(objects_app_path, self.options["sobject"] + ".object"),
            "w",
        ) as f:
            f.write(SOBJECT_METADATA.format(**self.options))
        with open("package.xml", "w") as f:
            f.write(PACKAGE_XML)

    def _run_task(self):
        describe_results = self.sf.Opportunity.describe()
        # Salesforce requires that at least one picklist value be present and active
        self.options["stage_name"] = next(filter(
            lambda pl: pl["active"],
            next(filter(
                lambda f: f["name"] == "StageName",
                describe_results["fields"]
            ))["picklistValues"]
        ))["value"]
        with temporary_dir() as tempdir:
            self.tempdir = tempdir
            self._build_package()

            d = Deploy(self.project_config, self.task_config, self.org_config, path=tempdir)
            d()
