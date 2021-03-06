from multipledispatch.dispatcher import (Dispatcher, MethodDispatcher,
        halt_ordering, restart_ordering, MDNotImplementedError)
from multipledispatch.utils import raises


def identity(x):
    return x


def inc(x):
    return x + 1


def dec(x):
    return x - 1


def test_dispatcher():
    f = Dispatcher('f')
    f.add((int,), inc)
    f.add((float,), dec)

    assert f.resolve((int,)) == inc
    assert f.dispatch(int) is inc

    assert f(1) == 2
    assert f(1.0) == 0.0


def test_union_types():
    f = Dispatcher('f')
    f.register((int, float))(inc)

    assert f(1) == 2
    assert f(1.0) == 2.0


def test_dispatcher_as_decorator():
    f = Dispatcher('f')

    @f.register(int)
    def inc(x):
        return x + 1

    @f.register(float)
    def inc(x):
        return x - 1

    assert f(1) == 2
    assert f(1.0) == 0.0


def test_register_instance_method():

    class Test(object):
        __init__ = MethodDispatcher('f')

        @__init__.register(list)
        def _init_list(self, data):
            self.data = data

        @__init__.register(object)
        def _init_obj(self, datum):
            self.data = [datum]

    a = Test(3)
    b = Test([3])
    assert a.data == b.data


def test_on_ambiguity():
    f = Dispatcher('f')

    identity = lambda x: x

    ambiguities = [False]
    def on_ambiguity(dispatcher, amb):
        ambiguities[0] = True


    f.add((object, object), identity, on_ambiguity=on_ambiguity)
    assert not ambiguities[0]
    f.add((object, float), identity, on_ambiguity=on_ambiguity)
    assert not ambiguities[0]
    f.add((float, object), identity, on_ambiguity=on_ambiguity)
    assert ambiguities[0]


def test_serializable():
    f = Dispatcher('f')
    f.add((int,), inc)
    f.add((float,), dec)
    f.add((object,), identity)

    import pickle
    assert isinstance(pickle.dumps(f), (str, bytes))

    g = pickle.loads(pickle.dumps(f))

    assert g(1) == 2
    assert g(1.0) == 0.0
    assert g('hello') == 'hello'


def test_raise_error_on_non_class():
    f = Dispatcher('f')
    assert raises(TypeError, lambda: f.add((1,), inc))


def test_docstring():

    def one(x, y):
        """ Docstring number one """
        return x + y

    def two(x, y):
        """ Docstring number two """
        return x + y

    def three(x, y):
        return x + y

    master_doc = 'Doc of the multimethod itself'

    f = Dispatcher('f', doc=master_doc)
    f.add((object, object), one)
    f.add((int, int), two)
    f.add((float, float), three)

    assert one.__doc__.strip() in f.__doc__
    assert two.__doc__.strip() in f.__doc__
    assert f.__doc__.find(one.__doc__.strip()) < \
            f.__doc__.find(two.__doc__.strip())
    assert 'object, object' in f.__doc__
    assert master_doc in f.__doc__


def test_halt_method_resolution():
    g = [0]
    def on_ambiguity(a, b):
        g[0] += 1

    f = Dispatcher('f')

    halt_ordering()

    def func(*args):
        pass

    f.add((int, object), func)
    f.add((object, int), func)

    assert g == [0]

    restart_ordering(on_ambiguity=on_ambiguity)

    assert g == [1]

    print(list(f.ordering))
    assert set(f.ordering) == set([(int, object), (object, int)])


def test_no_implementations():
    f = Dispatcher('f')
    assert raises(NotImplementedError, lambda: f('hello'))


def test_register_stacking():
    f = Dispatcher('f')

    @f.register(list)
    @f.register(tuple)
    def rev(x):
        return x[::-1]

    assert f((1, 2, 3)) == (3, 2, 1)
    assert f([1, 2, 3]) == [3, 2, 1]

    assert raises(NotImplementedError, lambda: f('hello'))
    assert rev('hello') == 'olleh'


def test_dispatch_method():
    f = Dispatcher('f')

    @f.register(list)
    def rev(x):
        return x[::-1]

    @f.register(int, int)
    def add(x, y):
        return x + y

    class MyList(list):
        pass

    assert f.dispatch(list) is rev
    assert f.dispatch(MyList) is rev
    assert f.dispatch(int, int) is add


def test_not_implemented():
    f = Dispatcher('f')

    @f.register(object)
    def _(x):
        return 'default'

    @f.register(int)
    def _(x):
        if x % 2 == 0:
            return 'even'
        else:
            raise MDNotImplementedError()

    assert f('hello') == 'default' # default behavior
    assert f(2) == 'even'          # specialized behavior
    assert f(3) == 'default'       # fall bac to default behavior
    assert raises(NotImplementedError, lambda: f(1, 2))


def test_not_implemented_error():
    f = Dispatcher('f')

    @f.register(float)
    def _(a):
        raise MDNotImplementedError()

    assert raises(NotImplementedError, lambda: f(1.0))
