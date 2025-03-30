document.getElementById('btn-occupied').addEventListener('click', function() {
    if (updateFloorSelect.value && updateZoneSelect.value && updateModuleSelect.value &&
        updateRoomSelect.value && selectedBed) {
      const bedId = `${updateFloorSelect.value}-${updateZoneSelect.value}-${updateModuleSelect.value}-${updateRoomSelect.value}-Cama${selectedBed}`;
      fetch(`/api/update-bed/${bedId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ estado: 'Ocupada' })
      })
      .then(response => response.json())
      .then(data => {
        document.getElementById('updateMessage').textContent = data.message;
      })
      .catch(error => console.error("Error:", error));
    } else {
      alert('Por favor, seleccione todos los campos y una cama.');
    }
  });
  
  document.getElementById('btn-unoccupied').addEventListener('click', function() {
    if (updateFloorSelect.value && updateZoneSelect.value && updateModuleSelect.value &&
        updateRoomSelect.value && selectedBed) {
      const bedId = `${updateFloorSelect.value}-${updateZoneSelect.value}-${updateModuleSelect.value}-${updateRoomSelect.value}-Cama${selectedBed}`;
      fetch(`/api/update-bed/${bedId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ estado: 'Desocupada' })
      })
      .then(response => response.json())
      .then(data => {
        document.getElementById('updateMessage').textContent = data.message;
      })
      .catch(error => console.error("Error:", error));
    } else {
      alert('Por favor, seleccione todos los campos y una cama.');
    }
  });
  