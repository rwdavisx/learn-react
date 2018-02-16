import React, { Component } from 'react';
import {MdSync} from 'react-icons/lib/md'
import './repost-button.css';

class RepostButton extends Component {
    constructor(props) {
        super(props);
        this.state = {
            amount: isNaN(this.props.num) || this.props.num === null ? 0 : this.props.num,
        }
    };

    render() {
        return (
        <div className={'repost-btn'}>
            <MdSync /><span>{this.state.amount}</span>
        </div>
        );
    };

    handleComment(input) {
        console.log(input);
    };
};

export default RepostButton;
