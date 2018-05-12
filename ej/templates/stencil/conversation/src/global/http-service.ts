// import greenlet from 'greenlet';

/*const fetchBeers = greenlet(
  function (page: number, style: number) {
    const key = '0ebd6396901832ee0176a008410ef5d9';
    const url = `https://cors-anywhere.herokuapp.com/http://api.brewerydb.com/v2/beers?key=${key}&p=${page}&styleId=${style}`;

    return fetch(url).then((res) => {
      return res.json()
    }).then((data) => {
      console.log(data.data);
      return data.data;
    })
  }
);*/

// const fetchBeers = (page: number, style: number = 1) => {
//   const key = '0ebd6396901832ee0176a008410ef5d9';
//   const url = `https://cors-anywhere.herokuapp.com/http://api.brewerydb.com/v2/beers?key=${key}&p=${page}&styleId=${style}`;

//   return fetch(url).then((res) => {
//     return res.json()
//   }).then((data) => {
//     console.log(data.data);
//     return data.data;
//   })
// }

// const fetchConversation = () => {
//   // const key = '0ebd6396901832ee0176a008410ef5d9';
//   const url = `http://localhost:3000/conversations/random`;

//   return fetch(url).then((res) => {
//     console.log('fetchConversation 1: ', res)
//     return res.json()
//   }).then((data) => {
//     console.log('fetchConversation 2: ', data)
//     console.log(data);
//     return data;
//   })
// }

const fetchConversation = () => {
  // const key = '0ebd6396901832ee0176a008410ef5d9';
  const url = `http://localhost:3000/conversations/random`;

  return fetch(url).then((res) => {
    console.log('fetchConversation 1: ', res)
    return res.json()
  })
}

// const fetchStyles = greenlet(
//   function () {
//     const key = '0ebd6396901832ee0176a008410ef5d9';
//     const url = `https://cors-anywhere.herokuapp.com/http://api.brewerydb.com/v2/styles?key=${key}`;

//     return fetch(url).then((res) => {
//       return res.json()
//     }).then((data) => {
//       return data.data;
//     })
//   }
// );

// const doSearch = greenlet(
//   function(searchTerm: string) {
//     const key = '0ebd6396901832ee0176a008410ef5d9';
//     const url = `https://cors-anywhere.herokuapp.com/http://api.brewerydb.com/v2/search?key=${key}&q=${searchTerm}&type=beer`;

//     return fetch(url).then((res) => {
//       return res.json()
//     }).then((data) => {
//       return data.data;
//     })
//   }
// );

// const getBeerDetail = greenlet(
//   function(id: string) {
//     const key = '0ebd6396901832ee0176a008410ef5d9';
//     const url = `https://cors-anywhere.herokuapp.com/http://api.brewerydb.com/v2/beer/${id}?key=${key}`;

//     return fetch(url).then((res) => {
//       return res.json()
//     }).then((data) => {
//       return data.data;
//     })
//   }
// )

export { fetchConversation};