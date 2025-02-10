import pydicom
import os
import shutil
from collections import defaultdict

def is_dicom_file(filepath):
    """Verifica si un fitxer és DICOM intentant llegir-lo."""
    try:
        with open(filepath, "rb") as f:
            preamble = f.read(132)
            return preamble[-4:] == b"DICM"  # Verifica el preàmbul DICOM
    except:
        return False

def get_study_description(ds, study_conditions):
    """
    Determina la StudyDescription basant-se en múltiples condicions DICOM.
    Ara comprova si 'ProtocolName' COMENÇA per un valor determinat.
    """
    protocol_name = ds.get("ProtocolName", "")

    for condition in study_conditions:
        conditions_met = True

        for tag, value in condition["conditions"].items():
            dicom_value = ds.get(tag, "")

            # Si és ProtocolName, comprovem que COMENÇA per un text
            if tag == "ProtocolName":
                if not dicom_value.startswith(value):
                    conditions_met = False
                    break
            else:
                if dicom_value != value:
                    conditions_met = False
                    break

        if conditions_met:
            return condition["study_description"]

    return "Generic Study"


# def find_value_by_tag(dicom_dir, target_tag):
#     """
#     Busca un fitxer DICOM que contingui un valor específic en un tag donat i retorna el seu valor.
#     """
#     for root, _, files in os.walk(dicom_dir):
#         for filename in files:
#             filepath = os.path.join(root, filename)
#             if not is_dicom_file(filepath):
#                 continue  # Saltar fitxers no DICOM

#             ds = pydicom.dcmread(filepath)
#             if ds.get("Modality", "") == "PET":
#                value = ds.get("{target_tag}, Unknown PET Study")
#                if value is not None:
#                    try:
#                        return value  # Convertir a número per poder comparar
#                    except ValueError:
#                        return None
    
#     return f"Unknown {target_value} Study"  # Retorna un valor per defecte si no troba cap coincidència

def find_pet_slices(dicom_dir, target_tag):
    """
    Busca un fitxer DICOM amb Modality = 'PET' a tota la carpeta
    i retorna el seu NumberOfSlices si existeix.
    """
    pet_slices = None

    for root, _, files in os.walk(dicom_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            if not is_dicom_file(filepath):
                continue  

            ds = pydicom.dcmread(filepath, stop_before_pixels=True)  # No carrega les imatges per ser més ràpid

            if ds.get("Modality", "") == "PT":
                num_slices = ds.get("NumberOfSlices", None)
                if num_slices is not None:
                    pet_slices = int(num_slices)  # Guarda el primer NumberOfSlices trobat
                    break  # Atura la cerca quan troba un PET amb NumberOfSlices

    return pet_slices  # Retorna None si no troba cap PET

def edit_dicom_tags(dicom_dir, output_dir, target_tag, target_value, modifications, study_conditions_PET_C, study_conditions_CS):
    """
    Edita els tags DICOM d'un estudi, buscant un valor específic en un tag DICOM donat.
    
    :param dicom_dir: Directori d'entrada amb els fitxers DICOM.
    :param output_dir: Directori de sortida on es guardaran els arxius modificats.
    :param target_tag: Tag DICOM que es vol buscar (ex: "Modality", "ProtocolName").
    :param target_value: Valor dins d'aquest tag a identificar (ex: "PET", "CT").
    :param modifications: Diccionari amb els tags a modificar {"Tag": "Nou Valor"}.
    :param study_conditions: Llista de condicions per modificar StudyDescription.
    """
    
    tvalue = find_pet_slices(dicom_dir, target_tag)
    print(f"{target_tag} = {tvalue}: {target_value}")

    # Decidir quines condicions d'estudi aplicar segons el valor numèric
    if tvalue is not None:
        if tvalue > int(target_value):
            study_conditions = study_conditions_CS
            print(f"Aplicant study_conditions_CS perquè {target_tag} = {tvalue} (> 300)")
        else:
            study_conditions = study_conditions_PET_C
            print(f"Aplicant study_conditions_PET perquè {target_tag} = {tvalue} (≤ 300)")
    else:
        study_conditions = study_conditions_CS
        print(f"Aplicant study_conditions_CS perquè {target_tag} = {tvalue}")
    
     
    for root, _, files in os.walk(dicom_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            if not is_dicom_file(filepath):
                continue  
            
            ds = pydicom.dcmread(filepath)

            # Aplicar modificacions generals
            for tag, value in modifications.items():
                if tag in ds:
                    ds.data_element(tag).value = value
                else:
                    setattr(ds, tag, value)

            # Aplicar StudyDescription segons les condicions triades
            ds.StudyDescription = get_study_description(ds, study_conditions)

           # Mantenir estructura de carpetes en output_dir
            relative_path = os.path.relpath(filepath, dicom_dir)
            output_filepath = os.path.join(output_dir, relative_path)
            os.makedirs(os.path.dirname(output_filepath), exist_ok=True)

            try:
                ds.save_as(output_filepath)
                #print(f"Guardat: {filepath}")
            except PermissionError:
                print(f"Error: No es pot escriure a {filepath}. Revisa els permisos.")


# Exemple d'ús
modifications = {
    "PatientName": "John Doe",
    "PatientID": "123456"
}

study_conditions_PET_C = [
    {"conditions": {"DeviceSerialNumber": "91252", "ProtocolName": "ALFA_TAU"}, "study_description": "FPM"},
    {"conditions": {"DeviceSerialNumber": "91252", "SeriesDescription": "Follow-up"}, "study_description": "Follow-up PET-CT Study"},
]


study_conditions_CS = [
    {"conditions": {"DeviceSerialNumber": "91252"}, "study_description": "Sarcopenia"},
]

dicom_input_dir = r"C:\Users\User\OneDrive - Hospital Clínic de Barcelona\Inf. Medica\XNAT\PET_inf"
dicom_output_dir = "output_dicom"
shutil.rmtree('output_dicom')

# Definir quin tag i valor volem buscar
target_tag = "NumberOfSlices"  # DicomTag que estem buscant
target_value = "300"  # Valor esperat dins del tag 

edit_dicom_tags(dicom_input_dir, dicom_output_dir, target_tag, target_value, modifications, study_conditions_PET_C, study_conditions_CS)