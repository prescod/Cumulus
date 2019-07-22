import os
import math
from collections import namedtuple
from cumulusci.tasks.bulkdata import LoadData
from cumulusci.core.utils import ordered_yaml_load
from cumulusci.utils import convert_to_snake_case, temporary_dir
from cumulusci.core.config import TaskConfig
from datetime import date
from datetime import timedelta
from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy import Unicode
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import create_session
from sqlalchemy import orm
from sqlalchemy.sql.expression import func
from .generate_bdi_data import BatchDataTask, init_db
from factory.alchemy import SQLAlchemyModelFactory
from factory import enums
import factory

START_DATE = date(2019, 1, 1)
enums.SPLITTER = "___"

class Adder:
    def __init__(self, x=0):
        self.x = x

    def __call__(self, value):
        self.x += value
        return int(self.x)
    
    def reset(self, x):
        self.x = x

def makeSFMeta(session):
    class SFMeta:
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "commit"
    return SFMeta


# SFactory could be a metaclass that injects the session
def make_factories(session, classes, SFactory):
    SFMeta = makeSFMeta(session)
    class PaymentFactory(SFactory):
        class Meta(SFMeta):
            model = classes.payments #

        class Params:
            date_adder_ = Adder(0)  # leading underscore breaks things.
            opportunity = "Opportunity not set"

        id = factory.Sequence(lambda n: n+1)
        amount = -1
        npe01__opportunity__c = factory.LazyAttribute(lambda o: o.opportunity and o.opportunity.id)
        payment_date = factory.LazyAttribute( lambda o: o.factory_parent.close_date)
        scheduled_date = factory.LazyAttribute(lambda o: o.payment_date)
        paid = factory.LazyAttribute(lambda o: o.factory_parent.factory_parent.payment_paid)

    class OpportunityFactory(SFactory):
        class Meta(SFMeta):
            model = classes.opportunities
            exclude = ("account", "primary_contact", "payment")
        class Params:
            with_payment = factory.Trait(
                payment = factory.RelatedFactory( PaymentFactory, "opportunity")
            )

        account = None
        primary_contact = None
        amount = "opportunity amount snot set"
        stage_name = "Prospecting"
        id = factory.Sequence(lambda n: n+1)
        name = factory.LazyAttribute(lambda o: f"{o.factory_parent.name} Donation")
        account_id = factory.LazyAttribute(lambda o: o.account and o.account.id)
        primary_contact__c = factory.LazyAttribute(lambda o: o.primary_contact and o.primary_contact.id)
        close_date = "Close date not set"
        payment = None

    class AccountFactory(SFactory):
        class Meta(SFMeta):
            model = classes.accounts 
            exclude = ("payment_paid", "with_payment")

        class Params:
            opportunity_date_adder = "Adder not set"  # leading underscore breaks things.
            payment_paid = -1
            with_payment = True
            opportunity___payment___amount = "Payment amount not set"
            opportunity = factory.RelatedFactory( OpportunityFactory, "account",
                with_payment=factory.LazyAttribute(lambda o: o.factory_parent.payment_paid > -1),
                close_date=factory.LazyAttribute(lambda o: START_DATE + timedelta(days=o.factory_parent.opportunity_date_adder(1)-1)),
            )

        id = factory.Sequence(lambda n: n+1)
        
        name = factory.LazyAttribute(lambda self: f'Account {self.id}')
        record_type = "Organization"

    class ContactFactory(SFactory):
        class Meta(SFMeta):
            model = classes.contacts #
            exclude = ("payment_paid", "with_payment")

        class Params:
            payment_paid = -1
            with_payment = True
            opportunity_date_adder = "Adder not set"  # leading underscore breaks things.
            opportunity___payment___amount = "Payment amount not set"
            opportunity = factory.RelatedFactory( OpportunityFactory, "primary_contact",
                with_payment=factory.LazyAttribute(lambda o: o.factory_parent.payment_paid > -1),
                close_date=factory.LazyAttribute(lambda o: START_DATE + timedelta(days=o.factory_parent.opportunity_date_adder(1)-1)),
            )

        id = factory.Sequence(lambda n: n + 1)
        name = factory.Sequence(lambda n: u'Contact %d' % (n + 1))

    class DataImportFactory(SFactory):
        class Meta(SFMeta):
            model = classes.npsp__DataImport__c

        class Params:
            date_adder = "Adder not set"  # leading underscore breaks things.
            ContactAdder = Adder(0)
            AccountAdder = Adder(0)

        id = factory.Sequence(lambda n: n+1)
        npsp__Donation_Date__c=factory.LazyAttribute(lambda o: START_DATE + timedelta(days=o.date_adder(1)-1))

        npsp__Do_Not_Automatically_Create_Payment__c = "FALSE"

        npsp__Account1_Name__c = None
        npsp__Contact1_Lastname__c = None


    return Factories(vars())

def Factories(stuff):
    factory_classes = {key: value for key, value in stuff.items()
                    if hasattr(value, "generate_batch")}
    FactoriesClass = namedtuple("Factories", factory_classes.keys())
    return FactoriesClass(**factory_classes)


class DataFactoryTask(BatchDataTask):
    def _generate_data(self, db_url, mapping_file_path, num_records):
        """Generate all of the data"""
        with open(mapping_file_path, "r") as f:
            mappings = ordered_yaml_load(f)

        session, base = init_db(db_url, mappings)
        factories = make_factories(session, base.classes, SQLAlchemyModelFactory)
        batch_size = math.floor(num_records / 10)
        self.make_preexisting_records(batch_size, factories)
        self.make_nonmatching_import_records(batch_size, factories)
        batch_size = math.floor(num_records / 4)
        self.make_matching_records(batch_size, factories)
        session.flush()
        session.commit()

    def make_preexisting_records(self, batch_size, factories):
        factories.AccountFactory.create_batch(batch_size, opportunity___amount=100,
                                               opportunity___payment___amount=100,
                                               payment_paid=False, 
                                              with_payment=True, opportunity_date_adder=Adder())
        factories.AccountFactory.create_batch(batch_size, opportunity___amount=200, payment_paid=False, 
                                                with_payment=True, opportunity_date_adder=Adder(),
                                                opportunity___payment___amount=200)
        factories.AccountFactory.create_batch(batch_size, opportunity___amount=300, payment_paid=False, 
                                                with_payment=True, opportunity_date_adder=Adder(),
                                                opportunity___payment___amount=50)
        factories.AccountFactory.create_batch(batch_size, opportunity___amount=400, payment_paid=True, 
                                                with_payment=True, opportunity_date_adder=Adder(),
                                                opportunity___payment___amount=50)
        factories.AccountFactory.create_batch(batch_size, opportunity___amount=500,
                                                with_payment=False, opportunity_date_adder=Adder())

        factories.ContactFactory.create_batch(batch_size, opportunity___amount=600, payment_paid=False,
                                                with_payment=False, opportunity_date_adder=Adder(),
                                                opportunity___payment___amount=600)
        factories.ContactFactory.create_batch(batch_size, opportunity___amount=700, payment_paid=False, 
                                                with_payment=False, opportunity_date_adder=Adder(),
                                                opportunity___payment___amount=700)
        factories.ContactFactory.create_batch(batch_size, opportunity___amount=800, payment_paid=False, 
                                                with_payment=False, opportunity_date_adder=Adder(),
                                                opportunity___payment___amount=50)
        factories.ContactFactory.create_batch(batch_size, opportunity___amount=900, payment_paid=True, 
                                                with_payment=False, opportunity_date_adder=Adder(),
                                                opportunity___payment___amount=50)
        factories.ContactFactory.create_batch(batch_size, opportunity___amount=1000, 
                                                with_payment=False, opportunity_date_adder=Adder())

    def make_nonmatching_import_records(self, batch_size, factories):
        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 100, 
                                                 npsp__Donation_Donor__c = "Account1",
                                                 npsp__Account1_Name__c = factory.LazyAttribute(lambda o: f"Account {o.AccountAdder(1)}"),
                                                 date_adder=Adder()
                                                 )
        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 200, 
                                                 npsp__Donation_Donor__c = "Account1", 
                                                 npsp__Account1_Name__c = factory.LazyAttribute(lambda o: f"Account {o.AccountAdder(1)}"),
                                                 npsp__Qualified_Date__c = '2020-01-01',
                                                 date_adder=Adder()                                                 
                                                 )
        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 50, 
                                                 npsp__Donation_Donor__c = "Account1",
                                                 npsp__Account1_Name__c = factory.LazyAttribute(lambda o: f"Account {o.AccountAdder(1)}"),
                                                 date_adder=Adder())
        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 400, 
                                                 npsp__Donation_Donor__c = "Account1",
                                                 npsp__Account1_Name__c = factory.LazyAttribute(lambda o: f"Account {o.AccountAdder(1)}"),
                                                 date_adder=Adder())
        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 500, 
                                                 npsp__Donation_Donor__c = "Account1",
                                                 npsp__Account1_Name__c = factory.LazyAttribute(lambda o: f"Account {o.AccountAdder(1)}"),
                                                 date_adder=Adder())
        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 600, 
                                                 npsp__Donation_Donor__c = "Contact1",
                                                 npsp__Contact1_Lastname__c = factory.LazyAttribute(lambda o: f"Contact {o.ContactAdder(1)}"),
                                                 date_adder=Adder())
        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 700, 
                                                 npsp__Donation_Donor__c = "Contact1",
                                                 npsp__Qualified_Date__c = '2020-01-01',
                                                 npsp__Contact1_Lastname__c = factory.LazyAttribute(lambda o: f"Contact {o.ContactAdder(1)}"),
                                                 date_adder=Adder())
        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 50, 
                                                 npsp__Donation_Donor__c = "Contact1",
                                                 npsp__Contact1_Lastname__c = factory.LazyAttribute(lambda o: f"Contact {o.ContactAdder(1)}"),
                                                 date_adder=Adder())
        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 900, 
                                                 npsp__Donation_Donor__c = "Contact1",
                                                 npsp__Contact1_Lastname__c = factory.LazyAttribute(lambda o: f"Contact {o.ContactAdder(1)}"),
                                                 date_adder=Adder())
        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 1000, 
                                                 npsp__Donation_Donor__c = "Contact1",
                                                 npsp__Contact1_Lastname__c = factory.LazyAttribute(lambda o: f"Contact {o.ContactAdder(1)}"),
                                                 date_adder=Adder())

    def make_matching_records(self, batch_size, factories):

        newadder = Adder(0)
        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 100, 
                    npsp__Donation_Donor__c = "Account1",
                    npsp__Do_Not_Automatically_Create_Payment__c = "FALSE",
                    npsp__Account1_Name__c = factory.LazyAttribute(lambda o: f"Account{o.AccountAdder(1)}"),
                    AccountAdder = newadder,
                    date_adder=Adder())

        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 200, 
            npsp__Donation_Donor__c = "Account1",
            npsp__Do_Not_Automatically_Create_Payment__c = "TRUE",
            npsp__Account1_Name__c = factory.LazyAttribute(lambda o: f"Account{o.AccountAdder(1)}"),
            AccountAdder = newadder,
            date_adder=Adder())

        contactadder = Adder(0)

        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 300,
            npsp__Donation_Donor__c = "Contact1",
            npsp__Do_Not_Automatically_Create_Payment__c = "FALSE",
            ContactAdder = contactadder,
            npsp__Contact1_Lastname__c = factory.LazyAttribute(lambda o: f"Contact{o.ContactAdder(1)}"),
            date_adder=Adder())

        factories.DataImportFactory.create_batch(batch_size, npsp__Donation_Amount__c = 400,
            npsp__Donation_Donor__c = "Contact1",
            npsp__Do_Not_Automatically_Create_Payment__c = "TRUE",
            npsp__Contact1_Lastname__c = factory.LazyAttribute(lambda o: f"Contact{o.ContactAdder(1)}"),
            ContactAdder = contactadder,
            date_adder=Adder())
