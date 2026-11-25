/**
 * Mapa de conectividade de uma porta (EV-0071).
 *
 * A porta liga-se a um cabo pela origem ou pelo destino; a «outra ponta» é a porta
 * do lado oposto do cabo. Não se inventa fibra nem destino: sem porta na outra ponta,
 * o destino fica `null` («Não conectado»).
 * @module portConnectivity
 */

/** @returns {{portId:number, portName:string|null, deviceName:string|null}|null} */
export function otherEnd(cable, portId) {
  if (!cable) return null
  const id = Number(portId)
  if (Number(cable.origin_port) === id) {
    return cable.destination_port
      ? { portId: cable.destination_port, portName: cable.destination_port_name || null, deviceName: cable.destination_device_name || null }
      : null
  }
  if (Number(cable.destination_port) === id) {
    return cable.origin_port
      ? { portId: cable.origin_port, portName: cable.origin_port_name || null, deviceName: cable.origin_device_name || null }
      : null
  }
  return null
}

/** Extensão em metros a partir de `length_km` (string decimal da API); null sem valor. */
export function cableLengthMeters(cable) {
  const km = Number(cable?.length_km)
  return cable?.length_km !== null && cable?.length_km !== undefined && cable?.length_km !== '' && Number.isFinite(km)
    ? Math.round(km * 1000)
    : null
}

/** Perda TX(esta) → RX(outra ponta), em dB; null se faltar qualquer leitura. */
export function linkLossDb(txHere, rxThere) {
  if (typeof txHere !== 'number' || typeof rxThere !== 'number') return null
  return Math.abs(txHere - rxThere)
}
