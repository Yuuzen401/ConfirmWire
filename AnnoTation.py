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

from .mesh_helpers import *
from .grease_pencil_helpers import *

class AnnoTation():
    annotation_name = "__ConfirmWireWorkingTemporaryAnnotation__"
    annotation_layer = None

    @classmethod
    def get_selected_edge_coords(self, bm, obj):
        selected_edge_coords = []
        edges = [e for e in bm.edges if e.select]
        for e in edges:
            v_1 = e.verts[0]
            v_2 = e.verts[1]
            n_1 = v_1.normal.copy()
            n_2 = v_2.normal.copy()
            co_1 = obj.matrix_world @ v_1.co.copy()
            co_2 = obj.matrix_world @ v_2.co.copy()
            selected_edge_coords.append(((co_1, n_1, v_1.index), (co_2, n_2, v_2.index)))
        return selected_edge_coords

    @classmethod
    def init_annotation_layer(self, context):
        self.remove_annotation_layer(context)
        layer = get_gp_layer(context, self.annotation_name)
        layer.color = (0, 1, 1)
        # layer.annotation_opacity = 0.1
        layer.thickness = 10
        self.annotation_layer = layer

    @classmethod
    def remove_annotation_layer(self, context):
        gp = context.scene.grease_pencil
        if gp is not None:
            for layer in list(gp.layers) :
                if self.annotation_name in layer.info :
                    gp.layers.remove( layer )

    @classmethod
    def selected_edge_to_annotation(self, context, selected_edge_coords):
        self.init_annotation_layer(context)
        frame = get_gp_frame(self.annotation_layer)
        for e in selected_edge_coords :
            stroke = frame.strokes.new()
            stroke.points.add(1)
            stroke.points[-1].co = e[0][0]
            stroke.points.add(1)
            stroke.points[-1].co = e[1][0]
            stroke.points.update()
        self.annotation_layer.hide = False

    @classmethod
    def toggle_annotation_view(self):
        if self.is_annotation_view():
            self.annotation_layer.hide = True
        else:
            self.annotation_layer.hide = False

    @classmethod
    def is_annotation_view(self):
        if self.annotation_layer is None:
            return False
        else:
            # hide が True なら 非表示になっているのでFalseを返す
            # hide が False なら 表示になっているのでTrueを返す
            return not self.annotation_layer.hide