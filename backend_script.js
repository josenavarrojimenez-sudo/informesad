/**
 * BACKEND UNIFICADO - Ciudad del Valle
 * Maneja dos tipos de datos:
 *   1. type=casa_edits          → ediciones del informe principal
 *   2. expedienteId=X           → estados de requisitos por lote (update.html)
 *   3. action=save&expedienteId → guardar expediente vía GET (evita CORS)
 *
 * INSTRUCCIONES:
 * 1. Abrí el Google Sheet (CDV Expedientes)
 * 2. Extensiones → Apps Script → reemplazá todo con este código
 * 3. Guardá → Implementar → Administrar implementaciones → editar → Nueva versión → Implementar
 * 4. Acceso: "Cualquier persona"
 */

const SECRET_TOKEN = "Adelante2025";
const SHEET_EXPEDIENTES = "EXPEDIENTES_DB";
const SHEET_CASAS = "CASAS_DB";

/**
 * GET:
 *   ?type=casa_edits                          → retorna ediciones del informe principal
 *   ?expedienteId=K.18                        → retorna expediente de ese lote
 *   ?action=save&token=X&expedienteId=Y&data= → GUARDA expediente vía GET (fix CORS)
 *   (sin params)                              → lista todos los expedientes
 */
function doGet(e) {
  try {
    const p = e.parameter || {};
    const action = p.action;
    const type = p.type;
    const expedienteId = p.expedienteId;

    // SAVE via GET (fix for CORS POST restriction)
    if (action === 'save') {
      if (p.token !== SECRET_TOKEN) return response({ status: "error", message: "Token inválido" });
      if (!expedienteId) return response({ status: "error", message: "Falta expedienteId" });

      const incoming = p.data ? JSON.parse(p.data) : {};
      const saveData = {
        statuses: incoming.statuses || {},
        updatedAt: new Date().toISOString()
      };

      const sheet = getOrCreateSheet(SHEET_EXPEDIENTES, ["EXPEDIENTE_ID", "JSON_DATA"]);
      const data = sheet.getDataRange().getValues();
      const rows = data.slice(1);
      let found = false;
      for (let i = 0; i < rows.length; i++) {
        if (rows[i][0] === expedienteId) {
          sheet.getRange(i + 2, 2).setValue(JSON.stringify(saveData));
          found = true; break;
        }
      }
      if (!found) sheet.appendRow([expedienteId, JSON.stringify(saveData)]);
      return response({ status: "ok", message: "Expediente guardado: " + expedienteId });
    }

    // SAVE CASAS via GET
    if (action === 'save_casas') {
      if (p.token !== SECRET_TOKEN) return response({ status: "error", message: "Token inválido" });
      const incoming = p.data ? JSON.parse(p.data) : [];
      const sheet = getOrCreateSheet(SHEET_CASAS, ["JSON_DATA"]);
      sheet.clear();
      sheet.appendRow(["JSON_DATA"]);
      sheet.appendRow([JSON.stringify(incoming)]);
      return response({ status: "ok", message: "Casas guardadas" });
    }

    // READ casa_edits
    if (type === 'casa_edits') {
      const sheet = getOrCreateSheet(SHEET_CASAS, ["JSON_DATA"]);
      const data = sheet.getDataRange().getValues();
      if (data.length <= 1) return response({ status: "ok", data: [] });
      const raw = data[1][0];
      const parsed = raw ? JSON.parse(raw) : [];
      return response({ status: "ok", data: parsed });
    }

    // READ expediente
    if (expedienteId) {
      const sheet = getOrCreateSheet(SHEET_EXPEDIENTES, ["EXPEDIENTE_ID", "JSON_DATA"]);
      const data = sheet.getDataRange().getValues();
      if (data.length <= 1) return response({ status: "ok", data: null });
      const rows = data.slice(1);
      const row = rows.find(r => r[0] === expedienteId);
      if (!row) return response({ status: "ok", data: null });
      return response({ status: "ok", data: JSON.parse(row[1]) });
    }

    // LIST expedientes
    const sheet = getOrCreateSheet(SHEET_EXPEDIENTES, ["EXPEDIENTE_ID", "JSON_DATA"]);
    const data = sheet.getDataRange().getValues();
    const ids = data.slice(1).map(r => r[0]).filter(Boolean);
    return response({ status: "ok", expedientes: ids });

  } catch (err) {
    return response({ status: "error", message: err.toString() });
  }
}

/**
 * POST (legacy — kept for casa_edits from index.html)
 */
function doPost(e) {
  try {
    const params = JSON.parse(e.postData.contents);
    if (params.token !== SECRET_TOKEN) return response({ status: "error", message: "Token inválido" });

    if (params.type === 'casa_edits') {
      const sheet = getOrCreateSheet(SHEET_CASAS, ["JSON_DATA"]);
      sheet.clear();
      sheet.appendRow(["JSON_DATA"]);
      sheet.appendRow([JSON.stringify(params.data || [])]);
      return response({ status: "ok", message: "Ediciones del informe guardadas" });
    }

    const expedienteId = params.expedienteId;
    if (!expedienteId) return response({ status: "error", message: "Falta expedienteId o type" });

    const saveData = {
      statuses: params.data ? params.data.statuses : {},
      updatedAt: new Date().toISOString()
    };

    const sheet = getOrCreateSheet(SHEET_EXPEDIENTES, ["EXPEDIENTE_ID", "JSON_DATA"]);
    const data = sheet.getDataRange().getValues();
    const rows = data.slice(1);
    let found = false;
    for (let i = 0; i < rows.length; i++) {
      if (rows[i][0] === expedienteId) {
        sheet.getRange(i + 2, 2).setValue(JSON.stringify(saveData));
        found = true; break;
      }
    }
    if (!found) sheet.appendRow([expedienteId, JSON.stringify(saveData)]);
    return response({ status: "ok", message: "Expediente guardado: " + expedienteId });

  } catch (err) {
    return response({ status: "error", message: err.toString() });
  }
}

function getOrCreateSheet(name, headers) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.appendRow(headers);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function response(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
