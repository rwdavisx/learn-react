import React, { Component } from 'react';
import { MdFavorite } from 'react-icons/lib/md';
import './like-button.css';

class LikeButton extends Component {
    constructor(props) {
        super(props);
        this.state = {
            amount: isNaN(this.props.num) || this.props.num === null ? 0 : this.props.num,
        }
    };

    render() {
        return (
            <div className={'like-btn'} onClick={() => this.handleLike()}>
                <MdFavorite /><span>{this.state.amount}</span>
            </div>
        );
    };

    handleLike() {
        let amt = this.state.amount;
        this.setState({amount: amt += 1});
    };
};

export default LikeButton;
