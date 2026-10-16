import bpy
# Helper function to get all F-Curves from an Action for both older and newer Blender versions
def get_all_fcurves(action):
    if hasattr(action, 'fcurves'):
        return list(action.fcurves)
    
    # Blender 5.0+ Slotted Actions fallback
    fcurves_list = []
    if hasattr(action, 'slots') and hasattr(action, 'layers'):
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    try:
                        # Attempt to get the channelbag for each slot
                        bag = strip.channelbag(slot)
                        if bag and hasattr(bag, 'fcurves'):
                            fcurves_list.extend(list(bag.fcurves))
                    except Exception:
                        continue
    return fcurves_list

# Helper function to find a specific F-Curve for both older and newer Blender versions
def find_fcurve(action, data_path, array_index=0):
    if hasattr(action, 'fcurves'):
        return action.fcurves.find(data_path, index=array_index)
    
    # Blender 5.0+ Slotted Actions fallback
    if hasattr(action, 'slots') and hasattr(action, 'layers'):
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    try:
                        bag = strip.channelbag(slot)
                        if bag and hasattr(bag, 'fcurves'):
                            # Find the F-Curve within the slot's channelbag
                            fc = bag.fcurves.find(data_path, index=array_index)
                            if fc:
                                return fc
                    except Exception:
                        continue
    return None

def remove_fcurve(action, fcurve):
    """Safely removes an F-Curve in Blender 4 (action) and Blender 5 (slotted channelbags)."""
    if hasattr(action, 'fcurves'):
        action.fcurves.remove(fcurve)
        return True
    
    # Blender 5.0+ Slotted Actions fallback
    if hasattr(action, 'slots') and hasattr(action, 'layers'):
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    try:
                        bag = strip.channelbag(slot)
                        if bag and hasattr(bag, 'fcurves'):
                            if fcurve in list(bag.fcurves):
                                bag.fcurves.remove(fcurve)
                                return True
                    except Exception:
                        continue
    return False