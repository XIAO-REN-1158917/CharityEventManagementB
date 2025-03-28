function sortTable(self, indendifier, columnIndex, datatype) {
  const table = self.parentNode.parentNode.parentNode;
  const rows = Array.from(table.rows).slice(1); // Skip header
  let sortedRows;
  const directions = directionsFor[indendifier];
  directions[columnIndex] = -1 * directions[columnIndex];

  if (datatype === 'usd') {
    // Sort by usd
    sortedRows = rows.sort((rowA, rowB) => {
      const amountA = parseFloat(
        rowA.cells[columnIndex].innerText.replace('$', '')
      );
      const amountB = parseFloat(
        rowB.cells[columnIndex].innerText.replace('$', '')
      );
      return (amountA - amountB) * directions[columnIndex];
    });
  } else if (datatype === 'datetime') {
    // Sort by datetime
    sortedRows = rows.sort((rowA, rowB) => {
      // const [dayA, monthA, yearA, hourA, minuteA, secondA] =
      //   rowA.cells[columnIndex].innerText.match(/\d+/g);
      // const dateA = new Date(
      //   `${yearA}-${monthA}-${dayA}T${hourA}:${minuteA}:${secondA}`
      // );

      // const [dayB, monthB, yearB, hourB, minuteB, secondB] =
      //   rowB.cells[columnIndex].innerText.match(/\d+/g);
      // const dateB = new Date(
      //   `${yearB}-${monthB}-${dayB}T${hourB}:${minuteB}:${secondB}`
      // );

      const dateA = new Date(rowA.cells[columnIndex].innerText);
      const dateB = new Date(rowB.cells[columnIndex].innerText);
      return (dateA - dateB) * directions[columnIndex];
    });
    // } else if (datatype === 'date') {
    //   // Sort by datetime
    //   sortedRows = rows.sort((rowA, rowB) => {
    //     const [dayA, monthA, yearA] =
    //       rowA.cells[columnIndex].innerText.match(/\d+/g);
    //     const dateA = new Date(`${yearA}-${monthA}-${dayA}`);

    //     const [dayB, monthB, yearB] =
    //       rowB.cells[columnIndex].innerText.match(/\d+/g);
    //     const dateB = new Date(`${yearB}-${monthB}-${dayB}`);

    //     return (dateA - dateB) * directions[columnIndex];
    //   });
  } else if (datatype === 'text') {
    // Sort by text (charity name)
    sortedRows = rows.sort((rowA, rowB) => {
      const textA = rowA.cells[columnIndex].innerText.toLowerCase();
      const textB = rowB.cells[columnIndex].innerText.toLowerCase();
      return directions[columnIndex] === 1
        ? textA.localeCompare(textB)
        : textB.localeCompare(textA);
    });
  } else if (datatype === 'number') {
    // Sort by text (charity name)
    sortedRows = rows.sort((rowA, rowB) => {
      const nA = parseFloat(rowA.cells[columnIndex].innerText);
      const nB = parseFloat(rowB.cells[columnIndex].innerText);
      return directions[columnIndex] * (nA - nB);
    });
  }

  // Append sorted rows back to the table body
  const tbody = table.tBodies[0];
  sortedRows.forEach((row) => tbody.appendChild(row));
}

async function postData(url = '', data = {}) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    referrerPolicy: 'no-referrer',
    body: JSON.stringify(data),
  });
  return response.json();
}

const modal = new bootstrap.Modal(document.getElementById('modal'));
function showModal(title, body, confirmCallback) {
  document.querySelector('.modal-title').innerHTML = title;
  document.querySelector('.modal-body').innerHTML = body;

  // remove all the listeners
  const confirmButton = document.getElementById('modal-confirm');
  const newButton = confirmButton.cloneNode(true);
  confirmButton.parentNode.replaceChild(newButton, confirmButton);

  newButton.addEventListener('click', (event) => {
    confirmCallback();
  });

  modal.show();
}

function hideModal() {
  modal.hide();
}

function str2dom(str) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(str, 'text/html');

  return doc.body.firstChild;
}
