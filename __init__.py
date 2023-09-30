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

bl_info = {
    "name": "ConfirmWire",
    "description": "check the edges",
    "author": "Yuuzen401",
    "version": (0, 0, 13),
    "blender": (2, 80, 0),
    "location":  "View3D > Sidebar > Confirm Wire",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "https://github.com/Yuuzen401/ConfirmWire",
    "category": "Object"
}

import bpy
import gpu
import bgl
import math
import random

from bpy.types import Operator, Panel, UIList, PropertyGroup
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty, BoolProperty, PointerProperty, CollectionProperty
from gpu_extras.batch import batch_for_shader
from .helper import *
from .mesh_helpers import *
from .Annotate import *

# Updater ops import, all setup in this file.
from . import addon_updater_ops

def update_cw_target(self, context):
    ConfirmWireOperator.force_disable()

class ConfirmWirePropertyGroup(PropertyGroup):

    # 対象オブジェクト
    cw_target : PointerProperty(name = "target", type = bpy.types.Object, poll = lambda self, obj: obj.type == 'MESH', update = update_cw_target)
    # 線の太さ
    cw_line_width : IntProperty(name = "width", default = 1, min = 1, max = 10)
    # 線の透明度
    cw_line_alpha : FloatProperty(name = "alpha", default = 0.5, min = 0, max = 1, precision = 1)
    # 線の色
    cw_line_color : FloatVectorProperty(name = 'color', subtype = 'COLOR', min = 0.0, max = 1, default = (0.0, 1.0, 0.0), precision = 1)
    # 左右反転するか
    cw_is_flip_horizontal : BoolProperty(name = "flip horizontal", default = False)
    # モディファイアの評価を有効にするか
    cw_is_modifier : BoolProperty(name = "modifier", default = False)
    # 隠れた線も表示するか
    cw_is_xray : BoolProperty(name = "xray", default = False)
    # 処理可能な頂点数
    cw_max_vertex : IntProperty(name = "max vertex", default = 100000, min = 10000, max = 200000)
    # 作成可能なアノテート
    cw_max_annotate : IntProperty(name = "max annotate", default = 10, min = 10, max = 40)

def update_hide(self, context):
    Annotate.set_annotate_layer_hide(context, self.hide, self.index)

def update_color(self, context):
    Annotate.set_annotate_layer_color(context, self.color, self.index)

@staticmethod
def get_opacity_value(opacity: bool):
    if opacity :
        return 0.2
    else :
        return 1

@staticmethod
def get_opacity_bool(opacity: float):
    if opacity == 1 :
        return False
    else :
        return True

def update_opacity(self, context):
    Annotate.set_annotate_layer_opacity(context, get_opacity_value(self.opacity), self.index)

class ConfirmWireAnnotateListPropertyGroup(PropertyGroup) :
    index: IntProperty(name = "confirm_wire_annotate_index", default = -1)
    hide: BoolProperty(name = "hide", default = False, update = update_hide)
    color: FloatVectorProperty(name = 'color', subtype = 'COLOR', min = 0.0, max = 1, default = (0.0, 1.0, 0.0), precision = 1, update = update_color)
    opacity: BoolProperty(name = "opacity", default = False, update = update_opacity)

class ConfirmWireOperator(Operator):
    bl_idname = "confirm_wire.operator"
    bl_label = "Confirm Wire"

    # 描画ハンドラ
    draw_handler = None

    @classmethod
    def is_enable(self):
        # 描画ハンドラがNone以外のときは描画中であるため、Trueを返す
        return True if self.draw_handler else False

    @classmethod
    def force_disable(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, 'WINDOW')
        self.draw_handler = None
        area_3d_view_tag_redraw_all()

    @classmethod
    def __handle_add(self, context):
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.__draw, (context, ), 'WINDOW', 'POST_VIEW')

    @classmethod
    def __handle_remove(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, 'WINDOW')
        self.draw_handler = None

    @classmethod
    def __draw(self, context):
        prop = context.scene.confirm_wire_prop
        obj = prop.cw_target
        bm = bmesh_copy_from_object(obj, True, False, prop.cw_is_modifier)

        # 頂点数が多すぎると負荷が高いため処理を中止する
        vertex_count = len(bm.verts)
        if vertex_count > prop.cw_max_vertex:
            bm.free()
            self.force_disable()
            show_message_error('canceled because there are too many vertices.')
            return

        indices = []
        indices_xray = []
        for e in bm.edges:
            v1 = e.verts[0]
            v2 = e.verts[1]
            normal = v1.normal + v2.normal

            # 左右反転か
            if prop.cw_is_flip_horizontal:
                normal.x = normal.x * -1

            # 3DVIEWから見て、法線の向きが内側であるか
            if is_in_normal_from_view_3d(context, normal):
                if prop.cw_is_xray:
                    indices_xray.append((e.verts[0].index, e.verts[1].index))
                continue

            indices.append((e.verts[0].index, e.verts[1].index))

        coords = []
        for v in bm.verts:
            co = v.co.copy()
            coords.append(co)

        if prop.cw_is_flip_horizontal:
            coords = [(v[0]*-1, v[1], v[2]) for v in coords]

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glLineWidth(prop.cw_line_width)

        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()
        rgb = prop.cw_line_color
        shader.uniform_float("color", (rgb[0], rgb[1], rgb[2], prop.cw_line_alpha))
        batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices = indices)
        batch.draw(shader)

        # 透過か
        if prop.cw_is_xray:
            batch_xray = batch_for_shader(shader, 'LINES', {"pos": coords}, indices = indices_xray)
            shader.uniform_float("color", (rgb[0], rgb[1], rgb[2], prop.cw_line_alpha * 0.5))
            batch_xray.draw(shader)

        bgl.glDisable(bgl.GL_BLEND)

        # 対象が編集時以外はbmeshを解放する
        if is_mesh_edit(obj) == False:
            bm.free()

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            # enable to disable
            if self.is_enable():
                self.__handle_remove(context)
            # disable to enable
            else:
                self.__handle_add(context)

            # 全エリアを再描画（アクティブな画面以外も再描画する）
            area_3d_view_tag_redraw_all()
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

class ConfirmWireAnnotateOperator(Operator):
    bl_idname = "confirm_wire_annotate.operator"
    bl_label = "Annotate"

    index: bpy.props.IntProperty(default = -1)

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            obj = context.active_object
            bm = bmesh_from_object(obj)
            selected_edge_coords = Annotate.get_selected_edge_coords(bm, obj)
            color = context.scene.confirm_wire_annotate_collection[self.index].color
            hide = context.scene.confirm_wire_annotate_collection[self.index].hide
            opacity = get_opacity_value(context.scene.confirm_wire_annotate_collection[self.index].opacity)
            
            Annotate.selected_edge_to_annotate(context, selected_edge_coords, color, hide, opacity, self.index)
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

# class ConfirmWireAnnotateViewOperator(Operator):
#     bl_idname = "confirm_wire_annotate_view.operator"
#     bl_label = "Annotate View"

#     index: bpy.props.IntProperty(default = -1)

#     def invoke(self, context, event):
#         if context.area.type == 'VIEW_3D':
#             Annotate.toggle_annotate_view(self.index)
#             return {'FINISHED'}
#         else:
#             return {'CANCELLED'}

class ConfirmWireAnnotateRemoveOperator(Operator):
    bl_idname = "confirm_wire_annotate_remove.operator"
    bl_label = "Annotate Remove"

    index: bpy.props.IntProperty(default = -1)

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            Annotate.remove_annotate_layer(context, self.index)
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

class ConfirmWireAnnotateInitOperator(Operator) :
    """アノテート一覧の初期化（明示的にボタン押さないと初期化不可）
    """
    bl_idname = "confirm_wire_annotate_init.operator"
    bl_label = ""
    bl_description = ""

    def execute(self, context) :
        context.scene.confirm_wire_annotate_collection.clear()
        cw_max_annotate = context.scene.confirm_wire_prop.cw_max_annotate
        for index in range(cw_max_annotate):
            annotate_layer = Annotate.get_annotate_layer(context, index)
            new_item = context.scene.confirm_wire_annotate_collection.add()
            new_item.index = index
            new_item.hide = False
            if annotate_layer is None:
                new_item.color = (random.random(), random.random(), random.random())
            else:
                new_item.color = annotate_layer.color
                new_item.hide = annotate_layer.hide
                new_item.opacity =  get_opacity_bool(annotate_layer.opacity)

        return {'FINISHED'}

class ConfirmWireAnnotateToSelectOperator(Operator) :
    """アノテートから選択する
    """

    index: bpy.props.IntProperty(default = -1)

    bl_idname = "confirm_wire_annotate_to_select.operator"
    bl_label = ""
    bl_description = ""

    def execute(self, context) :
        Annotate.annotate_to_select(context, self.index)
        return {'FINISHED'}

class ConfirmWireShowEdgeSeamsOperator(Operator) :
    """エッジのシーム表示を制御する
    """
    show_edge_seams: bpy.props.BoolProperty(default = True)

    bl_idname = "confirm_wire_edge_seams.operator"
    bl_label = ""
    bl_description = ""

    def execute(self, context) :
        overlay = context.space_data.overlay
        overlay.show_edge_seams = not self.show_edge_seams

        return {'FINISHED'}

class ConfirmWireShowEdgeBevelWeightOperator(Operator) :
    """エッジのシーム表示を制御する
    """
    show_edge_bevel_weight: bpy.props.BoolProperty(default = True)

    bl_idname = "confirm_wire_edge_bevel_weight.operator"
    bl_label = ""
    bl_description = ""

    def execute(self, context) :
        overlay = context.space_data.overlay
        overlay.show_edge_bevel_weight = not self.show_edge_bevel_weight

        return {'FINISHED'}

class ConfirmWireShowEdgeCreaseOperator(Operator) :
    """エッジのシーム表示を制御する
    """
    show_edge_crease: bpy.props.BoolProperty(default = True)

    bl_idname = "confirm_wire_edge_crease.operator"
    bl_label = ""
    bl_description = ""

    def execute(self, context) :
        overlay = context.space_data.overlay
        overlay.show_edge_crease = not self.show_edge_crease

        return {'FINISHED'}

class ConfirmWireShowEdgeSharpOperator(Operator) :
    """エッジのシーム表示を制御する
    """
    show_edge_sharp: bpy.props.BoolProperty(default = True)

    bl_idname = "confirm_wire_edge_sharp.operator"
    bl_label = ""
    bl_description = ""

    def execute(self, context) :
        overlay = context.space_data.overlay
        overlay.show_edge_sharp = not self.show_edge_sharp

        return {'FINISHED'}

class ConfirmWireAnnotateDummyOperator(Operator) :
    """ダミー
    """

    bl_idname = "confirm_wire_annotate_dummy.operator"
    bl_label = ""
    bl_description = ""

    def execute(self, context) :
        return {'FINISHED'}

class VIEW3D_PT_ConfirmWirePanel(Panel):
    bl_label = "Confirm Wire"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Confirm Wire"

    def draw(self, context):
        prop = context.scene.confirm_wire_prop
        layout = self.layout

        # -------------------------------------------------
        row = layout.row()
        row.scale_y = 1.5
        row.prop(prop, "cw_target")
        layout.separator()

        if prop.cw_target is None:
            return

        # -------------------------------------------------
        box = layout.box()

        row = box.row()
        row.label(text = 'line style')

        row = box.row()
        row.separator()
        row.prop(prop, "cw_line_width")

        row = box.row()
        row.separator()
        row.prop(prop, "cw_line_alpha")

        row = box.row()
        row.separator()
        row.prop(prop, "cw_line_color")

        # -------------------------------------------------
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.prop(prop, "cw_is_flip_horizontal", icon = "ARROW_LEFTRIGHT")
        row = layout.row()
        row.scale_y = 1.5
        row.prop(prop, "cw_is_modifier", icon = "MODIFIER")
        row = layout.row()
        row.scale_y = 1.5
        row.prop(prop, "cw_is_xray", icon = "XRAY")

        # -------------------------------------------------
        layout.separator()
        box = layout.box()
        row = box.row()
        row.scale_y = 2
        if ConfirmWireOperator.is_enable():
            row.operator(ConfirmWireOperator.bl_idname, text = "Confirm Wire Enable", depress = True,  icon = "PAUSE") 
        else:
            row.operator(ConfirmWireOperator.bl_idname, text = "Confirm Wire Enable", depress = False, icon = "PLAY")

        layout.separator()
        row = layout.row()
        row.prop(prop, "cw_max_vertex", icon = "OUTLINER_DATA_MESH")

class VIEW3D_UL_ConfirmWireAnnotateListLayout(UIList) :
    """アノテート一覧
    """
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index) :
        # オブジェクト名
        sp = layout.split(align=True, factor=0.2)
        sp.label(text = str(index))

        # カラー
        op = sp.prop(item, "color", text = "")

        # 書き込み
        op = sp.operator(ConfirmWireAnnotateOperator.bl_idname, text = "", icon = "GREASEPENCIL")
        op.index = index

        # 選択
        obj = context.active_object
        is_edit = obj and obj.mode == "EDIT" and obj.type == "MESH"
        if is_edit :
            op = sp.operator(ConfirmWireAnnotateToSelectOperator.bl_idname, text = "", icon = "SELECT_SET")
            op.index = index
        else :
            sp.operator(ConfirmWireAnnotateDummyOperator.bl_idname, text = "")

        # 表示 / 非表示
        if item.hide:
            sp.prop(item, "hide", text = "", icon = "HIDE_ON")
        else:
            sp.prop(item, "hide", text = "", icon = "HIDE_OFF")

        # 透過
        if item.opacity:
            sp.prop(item, "opacity", text = "", icon = "XRAY")
        else:
            sp.prop(item, "opacity", text = "", icon = "XRAY")

        # if Annotate.is_annotate_view(index):
        #     op = sp.operator(ConfirmWireAnnotateViewOperator.bl_idname, text = "", depress = True,  icon = "HIDE_OFF") 
        # else:
        #     op = sp.operator(ConfirmWireAnnotateViewOperator.bl_idname, text = "", depress = False, icon = "HIDE_ON")
        # op.index = index

        # 削除
        op = sp.operator(ConfirmWireAnnotateRemoveOperator.bl_idname, text = "", icon = "REMOVE")
        op.index = index

class VIEW3D_PT_ConfirmWireAnnotatePanel(Panel):
    bl_label = "Confirm Wire Annotate"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Confirm Wire"

    def draw(self, context):
        prop = context.scene.confirm_wire_prop
        layout = self.layout
        layout.label(text="Select --> Annotate", text_ctxt = "Select --> Annotate", icon = "GREASEPENCIL")
        row = layout.row()
        layout.label(text="Annotate --> Select", text_ctxt = "Annotate --> Select", icon = "SELECT_SET")
        row = layout.row()
        layout.label(text="Display Annotate", text_ctxt = "Display Annotate", icon = "HIDE_OFF")
        row = layout.row()
        layout.label(text="Opacity Annotate", text_ctxt = "Opacity Annotate", icon = "XRAY")
        row = layout.row()
        layout.label(text="Remove Annotate", text_ctxt = "Remove Annotate", icon = "REMOVE")
        row = layout.row()

        # アノテート一覧
        row.template_list(
            "VIEW3D_UL_ConfirmWireAnnotateListLayout",
            "",
            context.scene,
            "confirm_wire_annotate_collection",
            context.scene,
            "confirm_wire_annotate_active_index",
            rows = prop.cw_max_annotate)

        row = layout.row()
        row.scale_y = 1.5
        row.prop(prop, "cw_max_annotate", text="Max Annotate")
        row = layout.row()
        row.scale_y = 1.5
        row.operator(ConfirmWireAnnotateInitOperator.bl_idname, text = "Reload")

class VIEW3D_PT_ConfirmWireHelperPanel(Panel):
    bl_label = "Confirm Wire Helper"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Confirm Wire"

    def draw(self, context):
        overlay = context.space_data.overlay
        layout = self.layout
        sp = layout.split(align=True, factor=0.5)

        icon = "HIDE_OFF" if overlay.show_edge_crease else "HIDE_ON" 
        op = sp.operator(ConfirmWireShowEdgeCreaseOperator.bl_idname, depress = overlay.show_edge_crease, text = "Crease", text_ctxt = "Crease", icon = icon)
        op.show_edge_crease = overlay.show_edge_crease

        icon = "HIDE_OFF" if overlay.show_edge_sharp else "HIDE_ON" 
        op = sp.operator(ConfirmWireShowEdgeSharpOperator.bl_idname, depress = overlay.show_edge_sharp, text = "Sharp", text_ctxt = "Sharp", icon = icon)
        op.show_edge_sharp = overlay.show_edge_sharp

        sp = layout.split(align=True, factor=0.5)
        icon = "HIDE_OFF" if overlay.show_edge_bevel_weight else "HIDE_ON" 
        op = sp.operator(ConfirmWireShowEdgeBevelWeightOperator.bl_idname, depress = overlay.show_edge_bevel_weight, text = "Bevel", text_ctxt = "Bevel", icon = icon)
        op.show_edge_bevel_weight = overlay.show_edge_bevel_weight

        icon = "HIDE_OFF" if overlay.show_edge_seams else "HIDE_ON" 
        op = sp.operator(ConfirmWireShowEdgeSeamsOperator.bl_idname, depress = overlay.show_edge_seams, text = "Seams", text_ctxt = "Seams", icon = icon)
        op.show_edge_seams = overlay.show_edge_seams

@addon_updater_ops.make_annotations
class ConfirmWirePreferences(bpy.types.AddonPreferences):
    """ConfirmWire bare-bones preferences"""
    bl_idname = __package__

    # Addon updater preferences.

    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)

    updater_interval_months = bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0)

    updater_interval_days = bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31)

    updater_interval_hours = bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23)

    updater_interval_minutes = bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59)

    def draw(self, context):
        layout = self.layout

        # Works best if a column, or even just self.layout.
        mainrow = layout.row()
        col = mainrow.column()

        # Updater draw function, could also pass in col as third arg.
        addon_updater_ops.update_settings_ui(self, context)

        # Alternate draw function, which is more condensed and can be
        # placed within an existing draw function. Only contains:
        #   1) check for update/update now buttons
        #   2) toggle for auto-check (interval will be equal to what is set above)
        # addon_updater_ops.update_settings_ui_condensed(self, context, col)

        # Adding another column to help show the above condensed ui as one column
        # col = mainrow.column()
        # col.scale_y = 2
        # ops = col.operator("wm.url_open","Open webpage ")
        # ops.url=addon_updater_ops.updater.website

classes = (
    ConfirmWirePropertyGroup,
    ConfirmWireAnnotateListPropertyGroup,
    ConfirmWireOperator,
    ConfirmWireAnnotateOperator,
    # ConfirmWireAnnotateViewOperator,
    ConfirmWireAnnotateRemoveOperator,
    ConfirmWireAnnotateInitOperator,
    ConfirmWireAnnotateToSelectOperator,
    ConfirmWireShowEdgeSeamsOperator,
    ConfirmWireShowEdgeBevelWeightOperator,
    ConfirmWireShowEdgeCreaseOperator,
    ConfirmWireShowEdgeSharpOperator,
    ConfirmWireAnnotateDummyOperator,
    VIEW3D_PT_ConfirmWirePanel,
    VIEW3D_PT_ConfirmWireAnnotatePanel,
    VIEW3D_PT_ConfirmWireHelperPanel,
    ConfirmWirePreferences,
    VIEW3D_UL_ConfirmWireAnnotateListLayout,
    )

def register():
    addon_updater_ops.register(bl_info)
    for cls in classes:
        addon_updater_ops.make_annotations(cls)  # Avoid blender 2.8 warnings.
        bpy.utils.register_class(cls)
    bpy.types.Scene.confirm_wire_prop = PointerProperty(type = ConfirmWirePropertyGroup)
    bpy.types.Scene.confirm_wire_annotate_collection = CollectionProperty(type = ConfirmWireAnnotateListPropertyGroup)
    bpy.types.Scene.confirm_wire_annotate_active_index = IntProperty(name = "confirm_wire_annotate_active_index", default = -1)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.confirm_wire_prop
    del bpy.types.Scene.dynamic_solidify_collection 
    del bpy.types.Scene.dynamic_solidify_collection_active_index

    addon_updater_ops.unregister()

if __name__ == "__main__":
    register()