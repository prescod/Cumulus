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
enums.SPLITTER ="++"

Session = orm.scoped_session(orm.sessionmaker())

# SFactory could be a metaclass that injects the session
def make_factories(session, classes, SFactory):
    class PaymentFactory(SFactory):
        class Meta:
            model = classes.payments #
            sqlalchemy_session = Session   # the SQLAlchemy session object
            sqlalchemy_session_persistence = "commit"
            exclude = ("opportunity",)

        opportunity = "Opportunity not set"
        id = factory.Sequence(lambda n: n)
        npe01__opportunity__c = factory.LazyAttribute(lambda o: o.opportunity.id)
        amount = factory.LazyAttribute(lambda o: o.opportunity.amount)
        payment_date = factory.Sequence( lambda n: START_DATE + timedelta(days=n) )
        scheduled_date = factory.LazyAttribute(lambda o: o.payment_date)
        paid = False

    class OpportunityFactory(SFactory):
        class Meta:
            model = classes.opportunities
            sqlalchemy_session = Session   # the SQLAlchemy session object
            sqlalchemy_session_persistence = "commit"
            exclude = ("account", "_with_payment", "_payments")
        class Params:
            paid = factory.Trait(
                _payments = []
            )
            _with_payment = True
        account = None
        amount = "opportunity amount set"
        id = factory.Sequence(lambda n: n+1)
        name = factory.LazyAttribute(lambda o: f"Account {o.account.id} Donation")
        account_id = factory.LazyAttribute(lambda o: o.account.id)
        close_date = factory.Sequence( lambda n: START_DATE + timedelta(days=n) )
        _payments = factory.LazyAttribute(lambda o:
            PaymentFactory.create_batch(3, opportunity = o))

    class AccountFactory(SFactory):
        class Meta:
            model = classes.accounts 
            sqlalchemy_session = Session   # the SQLAlchemy session object
            sqlalchemy_session_persistence = "commit"
            exclude = ("_opportunities", "_amount", "_paid", "_with_payment")

        class Params:
            _amount = "Account amount not set"
            _paid = True
            _with_payment = True

        id = factory.Sequence(lambda n: n+1)
        
        name = factory.LazyAttribute(lambda self: f'Account {self.id}')
        record_type = "Organization"
        _opportunities = factory.RelatedFactoryList(OpportunityFactory, "account", 2,
            amount=factory.LazyAttribute(lambda o: o.factory_parent._amount),
            _with_payment=factory.LazyAttribute(lambda o: o.factory_parent._with_payment),
        )

    class ContactFactory(SFactory):
        class Meta:
            model = classes.contacts #
            sqlalchemy_session = Session   # the SQLAlchemy session object
            sqlalchemy_session_persistence = "commit"
            exclude = ("_opportunities", "_amount", "_paid", "_with_payment")

        class Params:
            _amount = "Account amount not set"
            _paid = True
            _with_payment = True

        id = factory.Sequence(lambda n: n)
        name = factory.Sequence(lambda n: u'Contact %d' % n)

    return Factories(vars())

def Factories(stuff):
    factory_classes = {key: value for key, value in stuff.items()
                    if hasattr(value, "generate_batch")}
    FactoriesClass = namedtuple("Factories", factory_classes.keys())
    return FactoriesClass(**factory_classes)


class DataFactoryTask(BatchDataTask):
    def _generate_data(self, db_url, mapping_file_path):
        """Generate all of the data"""
        with open(mapping_file_path, "r") as f:
            mappings = ordered_yaml_load(f)

        session, base = init_db(db_url, mappings)
        factories = make_factories(session, base.classes, SQLAlchemyModelFactory)
        num_records = int(self.options["num_records"])
        batch_size = math.floor(num_records / 10)
        self.make_all_records(batch_size, factories)
        # self.generate_bdi_denormalized_table(num_records)
        session.flush()
        session.commit()

    def make_all_records(self, batch_size, factories):
        factories.AccountFactory.create_batch(batch_size, _amount=100, _paid=False, _with_payment=True)
        factories.AccountFactory.create_batch(batch_size, _amount=200, _paid=False, _with_payment=True)
        factories.AccountFactory.create_batch(batch_size, _amount=300, _paid=False, _with_payment=True)
        factories.AccountFactory.create_batch(batch_size, _amount=400, _paid=True, _with_payment=True)
        factories.AccountFactory.create_batch(batch_size, _amount=500, _with_payment=False)

        factories.ContactFactory.create_batch(batch_size, _amount=500, _with_payment=False)
