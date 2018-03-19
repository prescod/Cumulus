
({
    doInit: function(cmp, event, helper){
        //query for the active filter group
        var activeFilterGroupId = cmp.get("v.activeFilterGroupId");
        if (activeFilterGroupId !== null) {
            var action = cmp.get("c.getFilterGroupById");
            action.setParams({id: activeFilterGroupId});

            action.setCallback(this, function (response) {
                var state = response.getState();
                if (state === "SUCCESS") {
                    //note: the parsing is important to avoid a shared reference
                    //todo: try to stringify on server side; only parse on client
                    //review: https://stackoverflow.com/questions/6605640/javascript-by-reference-vs-by-value
                    var data = JSON.parse(JSON.stringify(response.getReturnValue()));
                    cmp.set("v.activeFilterGroup", data.filterGroup);
                    cmp.set("v.cachedFilterGroupRollup", JSON.parse(JSON.stringify(response.getReturnValue())));

                    var labels = cmp.get("v.labels");

                    var actions = [{label: labels.edit, name: 'edit'}
                        , {label: labels.clone, name: 'clone'}
                        , {label: labels.delete, name: 'delete'}
                    ];

                    var filterRuleColumns = [{label: labels.object, fieldName: 'objectLabel', type: 'string'}
                        , {label: labels.field, fieldName: 'fieldLabel', type: 'string'}
                        , {label: labels.operator, fieldName: 'operator', type: 'string'}
                        , {label: labels.constant, fieldName: 'constant', type: 'string'}
                    ];
                    //todo: add actions back

                    cmp.set("v.filterRuleList", data.filterRuleList);
                    cmp.set("v.filterRuleColumns", filterRuleColumns);
                    helper.filterRollupList(cmp, data.filterGroup.MasterLabel, labels);

                }
                else if (state === "ERROR") {
                    var errors = response.getError();
                    if (errors) {
                        if (errors[0] && errors[0].message) {
                            console.log("Error message: " +
                                errors[0].message);
                        }
                    } else {
                        console.log("Unknown error");
                    }
                }
            });

            $A.enqueueAction(action);

        } else {

        }
    },

    createFilterRule: function(cmp, event, helper){
       //placeholder for creating a new filter rule
    },

    handleRowAction: function(cmp, event, helper){
        //placeholder for filter rule actions
    },

    onCancel: function(cmp, event, helper){
        //placeholder for on cancel function in !view mode

    },

    onSave: function(cmp, event, helper){
        //placeholder for on cancel function in !view mode

    },

    selectRollup: function(cmp, event, helper){
        //select rollup for navigation
        var rollupId = event.getParam('name');
        var filterGroupId = cmp.get("v.activeFilterGroupId");
        if(rollupId !== 'title'){
            var navEvent = $A.get("e.c:CRLP_NavigateEvent");
            navEvent.setParams({id: rollupId, target: 'rollup', lastId: filterGroupId});
            navEvent.fire();
        }
    }
})