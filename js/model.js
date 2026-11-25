/**
 * A0 离线推理：只做一次 logistic 回归点积，不发请求、不训练。
 * 输入是发售时已知信息；模型系数来自 data/ml/model.json。
 */
(function () {
  'use strict';

  function sigmoid(z) {
    if (z >= 0) {
      const e = Math.exp(-z);
      return 1 / (1 + e);
    }
    const e = Math.exp(z);
    return e / (1 + e);
  }

  /**
   * @param {object} model data/ml/model.json
   * @param {{main_genre:string, genres:string[], is_free:number, year:number}} input
   * @returns {number} P(reviews_12m >= 1000)
   */
  function predict(model, input) {
    if (!model || !Array.isArray(model.features)) {
      throw new Error('model.json 未加载');
    }
    const genres = new Set(input.genres || []);
    let z = Number(model.intercept) || 0;
    model.features.forEach((feature) => {
      let x = 0;
      if (feature.kind === 'main_genre') {
        x = input.main_genre === feature.value ? 1 : 0;
      } else if (feature.kind === 'genre') {
        x = genres.has(feature.value) ? 1 : 0;
      } else if (feature.name === 'is_free') {
        x = Number(input.is_free) ? 1 : 0;
      } else if (feature.name === 'year') {
        x = Number(input.year);
      }
      if (feature.scaled) {
        const std = Number(feature.std) || 1;
        x = (x - Number(feature.mean || 0)) / std;
      }
      z += Number(feature.coef || 0) * x;
    });
    return sigmoid(z);
  }

  window.ModelLab = { predict, sigmoid };
})();
