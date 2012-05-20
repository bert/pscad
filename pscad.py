# module pscad.py
#
# Copyright (C) 2012 Russ Dill <Russ.Dill@asu.edu>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

import copy
from numpy import eye, matrix
from decimal import Decimal as D
import dmath

def xform1(m, p):
    row = (m * matrix([ p[0], p[1], 1]).transpose()).transpose().tolist()[0]
    return (row[0], row[1])

def xform(m, p):
    try:
        return xform1(m, p)
    except:
        return [ xform(m, n) for n in p ]

def P(n):
    return str(n.quantize(D("0.000001"))) + "mm"

class pscad(object):
    def __init__(self):
        self.m = matrix(eye(3, dtype=D))
        self.points = []
        self.paths = []
        self.child = None
        self.next = None

    def __and__(a, b):
        n = a = copy.deepcopy(a)
        while n.child != None: n = n.child
        n.child = copy.deepcopy(b)
        return a

    def __or__(a, b):
        n = a = copy.deepcopy(a)
        while n.next != None: n = n.next
        n.next = copy.deepcopy(b)
        return a

    def pre(self):
        pass

    def fin(self):
        pass

    def do_render(self, meta, m = None, render = None):
        ret = []
        if m is None: m = matrix(eye(3, dtype=D))

        self.pre()
        try:
            render = self.render
        except:
            pass
        if render is not None:
            ret += render(self, m, meta)

        if self.child:
            ret += self.child.do_render(meta, m * self.m, render)
        self.fin()

        if self.next:
            ret += self.next.do_render(meta, m, render)

        return ret

class empty(pscad):
    def __init__(self):
        super(empty, self).__init__()

class union(pscad):
    current = []
    def __init__(self, name=None, skip=None):
        super(union, self).__init__()
        self.name = name
        self.cached = None
        self.added = False
        self.skip = skip
        
    def pre(self):
        if self.name is not None or (len(self.current) and self.current[0].name is not None):
            self.current.insert(0, self)
            self.added = True

    def fin(self):
        if self.added:
            self.current.remove(self)
            self.added = False

    def next_name(self):
        try:
            return self.name.next()
        except:
            return str(self.name)
 
    def __deepcopy__(self, arg):
        name = self.name
        self.name = None
        ret = copy.copy(self)
        self.name = name
        ret.name = name
        return ret

    @classmethod
    def get_name(cls):
        top = cls.current[0]
        if top.name is None:
            if top.cached is None:
                top.cached = cls.current[1].next_name()
            return top.cached
        else:
            return top.next_name()

    def should_skip(self, name):
        try:
            return name in self.skip
        except:
            try:
                return self.skip(name)
            except:
                pass
        return False

class back(pscad):
    back = False
    def __init__(self):
        super(back, self).__init__()

    @classmethod
    def pre(cls):
        cls.back = not cls.back

    @classmethod
    def fin(cls):
        cls.back = not cls.back

    @classmethod
    def set(cls):
        return cls.back

class paste(pscad):
    current = []
    def __init__(self, has=True):
        super(paste, self).__init__()
        self.should_have = has

    def pre(self):
        self.current.insert(0, self)

    def fin(self):
        self.current.pop(0)

    @classmethod
    def has(cls):
        return not len(cls.current) or cls.current[0].should_have

class nopaste(paste):
    def __init__(self):
        super(nopaste, self).__init__(False)

class multmatrix(pscad):
    def __init__(self, m = None):
        super(multmatrix, self).__init__()
        self.m = matrix(eye(3, dtype=D)) if m is None else m

class translate(multmatrix):
    def __init__(self, v):
        super(translate, self).__init__()
        self.m[0,2] = D(v[0])
        self.m[1,2] = D(v[1])

class rotate(multmatrix):
    def __init__(self, a):
        super(rotate, self).__init__()
        a = dmath.radians(D(a))
        self.m[0,0] = self.m[1,1] = D(dmath.cos(a))
        self.m[0,1] = D(dmath.sin(a))
        self.m[1,0] = -D(dmath.sin(a))

class scale(multmatrix):
    def __init__(self, v):
        super(scale, self).__init__()
        try:
            _v = [ v[0], v[1] ]
        except:
            v = [ v, v ]
        self.m[0,0] = D(v[0])
        self.m[1,1] = D(v[1])

class mirror(multmatrix):
    def __init__(self, v):
        super(mirror, self).__init__()
        a, b = D(v[0]), -D(v[1])
        a = a / dmath.hypot(a, b)
        b = b / dmath.hypot(a, b)
        self.m[0,0] = 1 - D(2) * a * a
        self.m[0,1] = - D(2) * a * b
        self.m[1,0] = - D(2) * a * b
        self.m[1,1] = 1 - D(2) * b * b

class shape(pscad):
    def __init__(self, v = None):
        super(shape, self).__init__()
        #self.paths = []

class polygon(shape):
    def __init__(self, points, paths = None):
        super(shape, self).__init__()
        self.points = points
        if paths is None:
            paths = range(len(points))
            paths.append(0)
        self.paths = paths

class square(shape):
    def __init__(self, v, center = False, rounded = False):
        super(square, self).__init__()
        try:
            v = [ D(v[0]), D(v[1]) ]
        except:
            v = [ D(v), D(v) ]
        o = (D(0), D(0)) if center else (v[0] / D(2), v[1] / D(2))
        self.points.append((o[0] - v[0] / D(2), o[1] - v[1] / D(2)))
        self.points.append((o[0] - v[0] / D(2), o[1] + v[1] / D(2)))
        self.points.append((o[0] + v[0] / D(2), o[1] + v[1] / D(2)))
        self.points.append((o[0] + v[0] / D(2), o[1] - v[1] / D(2)))
        self.paths.append([0, 1, 2, 3, 0])
        # Only for pads
        self.rounded = rounded

class point(shape):
    def __init__(self):
        super(point, self).__init__()
        self.points.append((D(0), D(0)))

class line(shape):
    def __init__(self, size, center = False):
        super(line, self).__init__()
        try:
            size = [ D(size[0]), D(size[1]) ]
        except:
            size = [ D(size), D(0) ]
        o = (D(0), D(0)) if center else (size[0] / D(2), size[1] / D(2))
        self.points.append((o[0] - size[0] / D(2), o[1] - size[1] / D(2)))
        self.points.append((o[0] + size[0] / D(2), o[1] + size[1] / D(2)))
        self.paths.append([0, 1])

class circle(shape):
    def __init__(self, r, sweep = None):
        super(circle, self).__init__()
        r = D(r)
        self.points.append((D(0), D(0)))
        self.points.append((r, D(0)))
        self.points.append((D(0), r))
        if sweep is not None:
            assert sweep > 0 and sweep < 360
            sweep = dmath.radians(D(sweep))
            self.points.append((dmath.cos(sweep) * r, dmath.sin(sweep) * r))
        self.full = sweep is None

class silk(pscad):
    def __init__(self, w):
        super(silk, self).__init__()
        self.w = D(w)

    def render(self, obj, m, meta):
        ret = []
        points = xform(m, obj.points)
        if type(obj) == circle:
            dx = []
            dy = []
            r = []
            a = []
            c = points[0]
            for p in points[1:]:
                dx.append(p[0] - c[0])
                dy.append(p[1] - c[1])
                r.append(dmath.hypot(dx[-1], dy[-1]))
                a.append(dmath.degrees(dmath.atan2(-dy[-1], dx[-1])))
            if obj.full:
                ret.append("ElementArc [ %s %s %s %s 0 360 %s ]" % (
                    P(c[0]), P(c[1]), P(r[0]), P(r[1]), P(self.w)))
            else:
                # Sweep direction should be clockwise (check for mirrored component)
                if (a[1] - a[0]) % 360 > 0:
                    sweep = a[0] - a[2]
                else:
                    sweep = a[2] - a[0]
                start = (a[0] % 360).quantize(D('1.00'))
                sweep = (sweep % 360).quantize(D('1.00'))
                ret.append("ElementArc [ %s %s %s %s %s %s %s ]" % (
                    P(c[0]), P(c[1]), P(r[0]), P(r[1]), start, sweep, P(self.w)))
                
        else:
           for path in obj.paths:
               for i in range(0, len(path) - 1):
                   p0 = points[path[i]]
                   p1 = points[path[i + 1]]
                   ret.append("ElementLine [ %s %s %s %s %s ]" % (
                       P(p0[0]), P(p0[1]), P(p1[0]), P(p1[1]), P(self.w)))
        return ret

class pad(union):
    def __init__(self, name, clearance, mask, skip=None):
        super(pad, self).__init__(name, skip)
        self.clearance = D(clearance)
        self.mask = D(mask)

    def rect_pad(self, name, points, rounded):
        m = []
        ret = []
        for i in range(len(points)):
            p0, p1 = points[i], points[(i + 1) % len(points)]
            m.append(((p0[0] + p1[0]) / D(2), (p0[1] + p1[1]) / D(2)))
        dim0 = dmath.hypot(m[2][0] - m[0][0], m[2][1] - m[0][1])
        dim1 = dmath.hypot(m[3][0] - m[1][0], m[3][1] - m[1][1])

        c = ((m[0][0] + m[2][0]) / D(2), (m[0][1] + m[2][1]) / D(2))

        if dim0.quantize(D("0.000001")) == dim1.quantize(D("0.000001")):
            if rounded:
                ret.append(circ_pad(name, c, dim0 / D(2)))
            else:
                ret += self.rect_pad(name, [ points[0], points[1], m[1], m[3] ], False)
                ret += self.rect_pad(name, [ m[3], m[1], points[2], points[3] ], False)
            return ret
        if dim0 > dim1:
            angle = dmath.atan2(m[2][1] - m[0][1], m[2][0] - m[0][0])
        else:
            angle = dmath.atan2(m[3][1] - m[1][1], m[3][0] - m[1][0])

        flags = []
        if not rounded:
            flags.append("square")
        if back.set():
            flags.append("onsolder")
        if not paste.has():
            flags.append("nopaste")

        thickness = min(dim0, dim1) / D(2)
        width = max(dim0, dim1) - thickness * D(2)
        p = []
        p.append((c[0] + dmath.cos(angle) * width / D(2), c[1] + dmath.sin(angle) * width / D(2)))
        p.append((c[0] - dmath.cos(angle) * width / D(2), c[1] - dmath.sin(angle) * width / D(2)))
        ret.append("""Pad [ %s %s %s %s %s %s %s "%s" "%s" "%s" ]""" % (
            P(p[0][0]), P(p[0][1]), P(p[1][0]), P(p[1][1]), P(thickness * D(2)),
            P(self.clearance * D(2)), P((self.mask + thickness) * D(2)), name, name,
            ",".join(flags)))
        return ret

    def circ_pad(self, name, c, r):
        flags = []
        if back.set():
            flags.append("onsolder")
        if not paste.has():
            flags.append("nopaste")
        return """Pad [ %s %s %s %s %s %s %s "%s" "%s" "%s" ]""" % (
            P(c[0]), P(c[1]), P(c[0]), P(c[1]), P(r * D(2)),
            P(self.clearance * D(2)), P((self.mask + r) * D(2)), name, name,
            ",".join(flags))

    def render(self, obj, m, meta):
        ret = []
        points = xform(m, obj.points)
        if type(obj) == circle:
            name = self.get_name()
            if self.should_skip(name): return ret
            dx = points[1][0] - points[0][0]
            dy = points[1][1] - points[0][1]
            r = dmath.hypot(dx, dy)
            ret.append(self.circ_pad(name, points[0], r))
        elif type(obj) == square:
            name = self.get_name()
            if self.should_skip(name): return ret
            p = []
            for i in range(0, len(obj.paths[0]) - 1):
                p.append(points[obj.paths[0][i]])
            ret += self.rect_pad(name, p, obj.rounded)
        elif type(obj) == union:
            pass

        return ret

class pin(union):
    def __init__(self, name, annulus, clearance, mask, square=False, skip=None):
        super(pin, self).__init__(name, skip)
        self.annulus = D(annulus)
        self.clearance = D(clearance)
        self.mask = D(mask)
        self.square = square

    def render(self, obj, m, meta):
        ret = []
        if type(obj) == circle:
            points = xform(m, obj.points)
            name = self.get_name()
            if self.should_skip(name): return ret
            dx = points[1][0] - points[0][0]
            dy = points[1][1] - points[0][1]
            r = dmath.hypot(dx, dy)
            ret.append("""Pin [ %s %s %s %s %s %s "%s" "%s" "" ]""" % (
                P(points[0][0]), P(points[0][1]), P((self.annulus + r) * D(2)),
                P(self.clearance * D(2)), P((self.annulus + self.mask + r) * D(2)),
                P(r * D(2)), name, name))
            if self.square:     
                sq = square((r + self.annulus) * D(2), center = True)
                un = union(name)
                np = nopaste()
                un.pre()
                np.pre()
                ret += pad(None, self.clearance, self.mask).render(sq, m, meta)
                back.pre()
                ret += pad(None, self.clearance, self.mask).render(sq, m, meta)
                back.fin()
                np.fin()
                un.fin()
        return ret

class hole(pscad):
    def __init__(self, clearance, mask):
        super(hole, self).__init__()
        self.clearance = D(clearance)
        self.mask = D(mask)

    def render(self, obj, m, meta):
        ret = []
        points = xform(m, obj.points)
        if type(obj) == circle:
            dx = points[1][0] - points[0][0]
            dy = points[1][1] - points[0][1]
            r = dmath.hypot(dx, dy)
            ret.append("""Pin [ %s %s %s %s %s %s "" "" "hole" ]""" % (
                P(points[0][0]), P(points[0][1]), P(r * D(2)),
                P(self.clearance * D(2)), P((self.mask + r) * D(2)),
                P(r * D(2))))
        return ret
 
class mark(pscad):
    def __init__(self):
        super(mark, self).__init__()

    def render(self, obj, m, meta):
        if len(obj.points) > 0:
            assert len(obj.points) == 1
            assert "mark" not in meta
            meta["mark"] = xform(m, obj.points[0])
        return []

class text(pscad):
    def __init__(self, sz = 100):
        super(text, self).__init__()
        self.sz = 100

    def render(self, obj, m, meta):
        if len(obj.points) > 0:
            assert len(obj.points) == 1
            assert "text" not in meta
            p0 = xform(m, obj.points[0])
            p1 = xform(m, (obj.points[0][0] + 1, obj.points[0][1]))
            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]
            scale = math.hypot(dx, dy)
            angle = (math.degrees(math.atan2(-dy, dx)) + 45) % 360
            meta["text"] = (p0, floor(angle / 90), scale * sz)
        return []

def element(n, desc):
    meta = dict()
    statements = n.do_render(meta)

    if "mark" in meta:
        m = meta["mark"]
    else:
        m = (D(0), D(0))

    if "text" in meta:
        t, dir, scale = meta["text"]
    else:
        t, dir, scale = (D(0), D(0)), 0, 100

    print """Element [0x00 "%s" "" "" %s %s %s %s %s %s 0x00]""" % (
        desc, P(m[0]), P(m[1]), P(t[0]), P(t[1]), dir, scale)
    print "("
    for statement in statements:
        print "\t" + statement
    print ")"

def up(v):
    return translate([0, -v])

def down(v):
    return translate([0, v])

def left(v):
    return translate([-v, 0])

def right(v):
    return translate([v, 0])

def rounded_square(v, r, center = False):
    if r == 0:
        return square(v, center)
    try:
        v = [ D(v[0]), D(v[1]) ]
    except:
        v = [ D(v), D(v) ]

    if r * D(2) == min(v):
        return square(v, center, rounded = True)

    assert r * D(2) < min(v)

    o = (D(0), D(0)) if center else (v[0] / D(2), v[1] / D(2))
    r = D(r)
    return union() & translate(o) & (
        square((v[0] - r * D(2), v[1] - r * D(2)), center = True) |
        left(v[0] / D(2) - r) & square([r * D(2), v[1]], center = True, rounded = True) |
        right(v[0] / D(2) - r) & square([r * D(2), v[1]], center = True, rounded = True) |
        up(v[1] / D(2) - r) & square([v[0], r * D(2)], center = True, rounded = True) |
        down(v[1] / D(2) - r) & square([v[0], r * D(2)], center = True, rounded = True)
    )

def row(obj, pitch, n, center = False):
    ret = pscad()
    for i in range(n):
        ret |= (right(i * pitch) & obj)
    if center:
        return left(pitch * (n - 1) / D(2)) & ret
    else:
        return ret

