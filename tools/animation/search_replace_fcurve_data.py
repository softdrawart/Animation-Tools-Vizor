import bpy, re

def get_armatures(self, context):
    return [(obj.name, obj.name, "") for obj in bpy.data.objects if obj.type == 'ARMATURE'] or [("", "No Armatures", "")]

class ReplaceFCurveDataPathOperator(bpy.types.Operator):
    """Replace part of the data_path in the active action's FCurves"""
    bl_idname = "action.replace_fcurve_data_path"
    bl_label = "Replace Data Path"
    bl_options = {'REGISTER', 'UNDO'}

    rename_all: bpy.props.BoolProperty(name="Rename all", default=False)
    
    @staticmethod
    def get_mirrored_name(name: str) -> str:
        if ".L" in name:
            return name.replace(".L", ".R")
        elif ".R" in name:
            return name.replace(".R", ".L")
        elif ".l" in name:
            return name.replace(".l", ".r")
        elif ".r" in name:
            return name.replace(".r", ".l")
        elif "Left" in name:
            return name.replace("Left", "Right")
        elif "Right" in name:
            return name.replace("Right", "Left")
        elif "left" in name:
            return name.replace("left", "right")
        elif "right" in name:
            return name.replace("right", "left")
        else:
            return name  # no recognizable side marker
        
    def rename(self, armature_name: str, find_text: str, replace_text: str, rename_mirror = False):
        assert armature_name and find_text and replace_text

        if rename_mirror:
            mirror_find = self.get_mirrored_name(find_text)
            mirror_replace = self.get_mirrored_name(replace_text)
        
        if armature_name not in bpy.data.objects:
            self.report({'WARNING'}, "Selected armature not found")
            return {'CANCELLED'}
        
        obj = bpy.data.objects[armature_name]
        if not obj or not obj.animation_data or not obj.animation_data.action:
            self.report({'WARNING'}, "No active action found")
            return {'CANCELLED'}

        action = obj.animation_data.action
        #search and replace group and fcurve data_path
        
        for group in action.groups:
            if find_text == group.name:
                group.name = replace_text
            if rename_mirror:
                if mirror_find == group.name:
                    group.name =  mirror_replace

        pattern = re.compile(r'pose\.bones\["(.*?)"\]')
        for fcurve in action.fcurves:
            path = fcurve.data_path
            bone_name = pattern.search(path).group(1)

            if find_text == bone_name:
                fcurve.data_path = fcurve.data_path.replace(find_text, replace_text)
                print(f"replaced {find_text} --> {replace_text}")
            elif rename_mirror:
                if mirror_find == bone_name:
                    fcurve.data_path = fcurve.data_path.replace(mirror_find, mirror_replace)
                    print(f"replaced {mirror_find} --> {mirror_replace}")
    def execute(self, context):
        if self.rename_all and context.scene.selected_armature:
            #rename all
            if context.scene.bone_pairs:
                for item in context.scene.bone_pairs:
                    self.rename(context.scene.selected_armature, item.ren_from, item.ren_to, context.scene.rename_mirror)
        else:
            #rename single
            find_text = context.scene.find_text
            replace_text = context.scene.replace_text
            armature_name = context.scene.selected_armature
            rename_mirror = context.scene.rename_mirror
            self.rename(armature_name, find_text, replace_text, rename_mirror)
        return {'FINISHED'}

# Step 1: Define the PropertyGroup for a bone pair
class BonePair(bpy.types.PropertyGroup):
    ren_from: bpy.props.StringProperty(name="Source Bone Name")
    ren_to: bpy.props.StringProperty(name="Target Bone Name")

# Step 2: Define the UIList class
class BonePair_UL_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "ren_from", text='')
        row.scale_x=0.1
        row.label(text="→")
        row.scale_x=1
        row.prop(item, "ren_to", text='')

    def draw_filter(self, context, layout):
        layout.prop(self, "filter_name", text="", icon='VIEWZOOM')

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)

        helper_func = bpy.types.UI_UL_list

        flt_flags = helper_func.filter_items_by_name(self.filter_name, self.bitflag_filter_item, items, "ren_from")
        return flt_flags, []

# Step 3: Define operators to add/remove bone pairs
class BONEPAIR_OT_Add(bpy.types.Operator):
    bl_idname = "bonepair.add"
    bl_label = "Add Bone Pair"
    bl_description = "Adds currently set bone pair in the list"
    
    def execute(self, context):
        scene = context.scene
        find = scene.find_text
        replace = scene.replace_text

        # Check if such a pair already exists and both sides are not empty
        exists = any(
            p.ren_from == find and p.ren_to == replace
            for p in scene.bone_pairs
            if p.ren_from and p.ren_to
        )

        if not exists and find and replace:
            pair = scene.bone_pairs.add()
            pair.ren_from = find
            pair.ren_to = replace
            return {'FINISHED'}
        else:
            self.report({'INFO'}, "Pair already exists or is incomplete")
            return {'CANCELLED'}

class BONEPAIR_OT_Remove(bpy.types.Operator):
    bl_idname = "bonepair.remove"
    bl_label = "Remove Bone Pair"
    bl_description = "Remove selected bone pair in the list"
    def execute(self, context):
        idx = context.scene.bone_pairs_index
        if context.scene.bone_pairs and idx < len(context.scene.bone_pairs):
            context.scene.bone_pairs.remove(idx)
            context.scene.bone_pairs_index = max(0, idx - 1)
        return {'FINISHED'}
    
class ReplaceFCurveDataPathPanel(bpy.types.Panel):
    """Creates a Panel in the UI to replace FCurve data paths"""
    bl_label = "Replace FCurve Data Path"
    bl_idname = "ACTION_PT_replace_fcurve_data_path"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "selected_armature", text="Armature")
        row = layout.row()
        row.prop(scene, "find_text")
        row.operator("action.pick_bone", icon="EYEDROPPER").target = "find_text"
        row = layout.row()
        row.prop(scene, "replace_text")
        row.operator("action.pick_bone", icon="EYEDROPPER").target = "replace_text"
        layout.prop(scene, "rename_mirror", text="Rename Mirror")
        layout.operator(ReplaceFCurveDataPathOperator.bl_idname)

        #multiple fcurve rename
        layout.label(text="Editing Bone Pairs")
        layout.template_list("BonePair_UL_List", "", scene, "bone_pairs", scene, "bone_pairs_index")

        row = layout.row(align=True)
        row.operator(BONEPAIR_OT_Add.bl_idname, icon='ADD')
        row.operator(BONEPAIR_OT_Remove.bl_idname, icon='REMOVE')
        
        layout.operator(ReplaceFCurveDataPathOperator.bl_idname).rename_all = True
        row = layout.row(align=True)
        row.operator(EXPORT_OT_bone_pairs.bl_idname)
        row.operator(IMPORT_OT_bone_pairs.bl_idname)

class EXPORT_OT_bone_pairs(bpy.types.Operator):
    bl_idname = "export.bone_pairs"
    bl_label = "Export Bone Pairs"
    bl_description = "Export bone rename pairs to a text file"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        items = context.scene.bone_pairs
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                for item in items:
                    f.write(f"{item.ren_from},{item.ren_to}\n")
            self.report({'INFO'}, "Export successful")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {e}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        self.filepath = "bone_pairs.txt"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class IMPORT_OT_bone_pairs(bpy.types.Operator):
    bl_idname = "import.bone_pairs"
    bl_label = "Import Bone Pairs"
    bl_description = "Import bone rename pairs from a text file"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        scene = context.scene
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            scene.bone_pairs.clear()
            for line in lines:
                parts = line.strip().split(',')
                if len(parts) == 2:
                    item = scene.bone_pairs.add()
                    item.ren_from = parts[0].strip()
                    item.ren_to = parts[1].strip()

            self.report({'INFO'}, "Import successful")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class PickBoneOperator(bpy.types.Operator):
    """Pick selected bone for Find or Replace field"""
    bl_idname = "action.pick_bone"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}

    target: bpy.props.StringProperty()

    @classmethod
    def poll(self, context):
        return context.active_object and context.active_object.type == 'ARMATURE' and context.active_object.mode == 'POSE'

    def execute(self, context):
        armature = bpy.context.active_object
        if armature and armature.type == 'ARMATURE' and armature.mode == 'POSE':
            bone = bpy.context.active_pose_bone
            if bone:
                setattr(context.scene, self.target, bone.name)
                self.report({'INFO'}, f"Set {self.target} to {bone.name}")
                return {'FINISHED'}
        self.report({'WARNING'}, "No active bone selected")
        return {'CANCELLED'}

classes = [
    ReplaceFCurveDataPathOperator,
    PickBoneOperator,
    BonePair,
    BonePair_UL_List,
    BONEPAIR_OT_Add,
    BONEPAIR_OT_Remove,
    EXPORT_OT_bone_pairs,
    IMPORT_OT_bone_pairs,
    ReplaceFCurveDataPathPanel,
]

def register():
    scene = bpy.types.Scene
    props = bpy.props
    scene.find_text = props.StringProperty(name="Find", description="Old name")
    scene.replace_text = props.StringProperty(name="Replace", description="New name")
    scene.selected_armature = props.EnumProperty(name="Armature", items=get_armatures, description="Armature name")
    scene.rename_mirror = props.BoolProperty(name="Rename Mirror", default=False, description="Mirror sides")
    scene.bone_pairs = props.CollectionProperty(type=BonePair)
    scene.bone_pairs_index = props.IntProperty()

    for cls in classes:
        bpy.utils.register_class(cls)
    


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.find_text
    del bpy.types.Scene.replace_text
    del bpy.types.Scene.selected_armature
    del bpy.types.Scene.rename_mirror
    del bpy.types.Scene.bone_pairs
    del bpy.types.Scene.bone_pairs_index

if __name__ == "__main__":
    register()
