# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import mathutils

from .mesh_helpers import *
from .grease_pencil_helpers import *

class Annotate():
    annotate_name = "__Annotate__"
    # annotate_layer = {}

    @classmethod
    def get_selected_edge_coords(self, bm, obj):
        selected_edge_coords = []
        edges = [e for e in bm.edges if e.select]
        for e in edges:
            v_1 = e.verts[0]
            v_2 = e.verts[1]
            # n_1 = v_1.normal.copy()
            # n_2 = v_2.normal.copy()
            co_1 = obj.matrix_world @ v_1.co.copy()
            co_2 = obj.matrix_world @ v_2.co.copy()
            selected_edge_coords.append((co_1, co_2))
            # selected_edge_coords.append(((co_1, n_1, v_1.index), (co_2, n_2, v_2.index)))
        return selected_edge_coords

    @classmethod
    def init_annotate_layer(self, context, color, hide, opacity, index = -1):
        self.remove_annotate_layer(context, index)
        annotate_layer = self.create_annotate_layer(context, index)
        annotate_layer.color = color
        annotate_layer.hide = hide
        annotate_layer.opacity = opacity
        annotate_layer.thickness = 10

    @classmethod
    def set_annotate_layer_color(self, context, color, index = -1):        
        annotate_layer = self.get_annotate_layer(context, index)
        if annotate_layer is None:
            return
        annotate_layer.color = color

    @classmethod
    def set_annotate_layer_hide(self, context, hide, index = -1):        
        annotate_layer = self.get_annotate_layer(context, index)
        if annotate_layer is None:
            return
        annotate_layer.hide = hide

    @classmethod
    def set_annotate_layer_opacity(self, context, opacity, index = -1):        
        annotate_layer = self.get_annotate_layer(context, index)
        if annotate_layer is None:
            return
        annotate_layer.opacity = opacity

    @classmethod
    def get_annotate_layer(self, context, index = -1):
        return get_gp_layer(context, self.get_annotate_name(index), False)

    @classmethod
    def create_annotate_layer(self, context, index = -1):
        return get_gp_layer(context, self.get_annotate_name(index))

    @classmethod
    def remove_annotate_layer(self, context, index = -1):
        annotate_layer = self.get_annotate_layer(context, index)
        if annotate_layer is None:
            return
        gp = context.scene.grease_pencil
        if gp is not None:
            for layer in list(gp.layers) :
                if self.get_annotate_name(index) in layer.info :
                    annotate_layer.hide = True
                    gp.layers.remove(layer)

    @classmethod
    def get_annotate_name(self, index = -1):
        if index is -1:
            annotate_name = self.annotate_name
        else:
            annotate_name = self.annotate_name + str(index)
        return annotate_name

    @classmethod
    def selected_edge_to_annotate(self, context, selected_edge_coords, color, hide, opacity, index = -1):
        self.init_annotate_layer(context, color, hide, opacity, index)
        annotate_layer = self.get_annotate_layer(context, index)
        if annotate_layer is None:
            return
        frame = get_gp_frame(annotate_layer)
        for e in selected_edge_coords :
            stroke = frame.strokes.new()
            stroke.points.add(1)
            stroke.points[-1].co = e[0]
            # stroke.points[-1].co = e[0][0]
            stroke.points.add(1)
            stroke.points[-1].co = e[1]
            # stroke.points[-1].co = e[1][0]
            stroke.points.update()

    @classmethod
    def annotate_to_select(self, context, index = -1):
        annotate_layer = self.get_annotate_layer(context, index)
        if annotate_layer is None:
            return
        frame = get_gp_frame(annotate_layer)
        strokes = frame.strokes
        co_list = []
        for i, _stroke in enumerate(strokes):
            stroke_points = strokes[i].points
            for point in stroke_points :
                co_list.append((point.co.x, point.co.y, point.co.z))

        if co_list :
            obj = bpy.context.edit_object
            bm = bmesh_from_object(obj)
            bm.verts.ensure_lookup_table()
            size = len(bm.verts)
            kd = mathutils.kdtree.KDTree(size)
            
            for i, v in enumerate(bm.verts):
                kd.insert(v.co, i)
            
            kd.balance()

            for co in co_list :
                co_find = co
                co, v_index, dist = kd.find(co_find)
                # 完全一致である場合のみ選択する
                if 0 == dist :
                    bm.verts[v_index].select = True

            bmesh.update_edit_mesh(obj.data)
            bm.select_flush(True)

    # @classmethod
    # def toggle_annotate_view(self, index = -1):
    #     annotate_layer = annotate_layer = self.get_annotate_layer(index)
    #     if annotate_layer is None:
    #         return
    #     if self.is_annotate_view(index):
    #         annotate_layer.hide = True
    #     else:
    #         annotate_layer.hide = False

    # @classmethod
    # def is_annotate_view(self, index = -1):
    #     annotate_layer = annotate_layer = self.get_annotate_layer(index)
    #     if annotate_layer is None:
    #         return False
    #     else:
    #         # hide が True なら 非表示になっているのでFalseを返す
    #         # hide が False なら 表示になっているのでTrueを返す
    #         return not annotate_layer.hide