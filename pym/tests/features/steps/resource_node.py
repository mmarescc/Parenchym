from behave import (
    given, when, then
)
from pym.resmgr.models import ResourceNode
from pym.authmgr.const import UNIT_TESTER_UID


@given('my root node is {name}/{kind}')
def step_impl(context, name, kind):
    context.root_node = ResourceNode.create_root(context.sess,
        owner=UNIT_TESTER_UID, name=name, kind=kind)


@when('I create a new root node entry')
def step_impl(context):
    context.sess.add(context.root_node)
    context.sess.flush()


@then('I should find new root node in restree table')
def step_impl(context):
    root_node = ResourceNode.load_root(context.sess, context.root_node.name)
    assert root_node


# --


@given('my root node {name}/{kind} already exists')
def step_impl(context, name, kind):
    context.name = name
    context.kind = kind
    context.existing_root_node = ResourceNode.create_root(context.sess,
        owner=UNIT_TESTER_UID, name=name, kind=kind)
    context.sess.flush()


@when('I create a new root node entry with this name and kind')
def step_impl(context):
    context.new_root_node = ResourceNode.create_root(context.sess,
        owner=UNIT_TESTER_UID, name=context.name, kind=context.kind)
    context.sess.flush()


@then('I get the existing one')
def step_impl(context):
    assert context.existing_root_node.id == context.new_root_node.id


# --


@given('root node {name}/{kind} already exists')
def step_impl(context, name, kind):
    context.name = name
    context.kind = kind
    context.existing_root_node = ResourceNode.create_root(context.sess,
        owner=UNIT_TESTER_UID, name=name, kind=kind)
    context.sess.flush()


@when('I create a new root node with this name but different kind')
def step_impl(context):
    context.other_kind = context.kind + '2'


@then('a ValueError exception is thrown')
def step_impl(context):
    try:
        ResourceNode.create_root(context.sess,
            owner=UNIT_TESTER_UID, name=context.name, kind=context.other_kind)
    except ValueError:
        assert True
    else:
        assert False  # No exception occurred


